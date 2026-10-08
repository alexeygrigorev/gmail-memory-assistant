const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
const path=require('node:path');
function setup(fetch){
 let connect,message,disconnect;const sent=[];
 const port={name:'mem-hub',onMessage:{addListener:f=>message=f},onDisconnect:{addListener:f=>disconnect=f},postMessage:event=>{if(port.closed)throw Error('disconnected');sent.push(event)}};
 const chrome={runtime:{lastError:undefined,onConnect:{addListener:f=>connect=f}}};
 vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../extension/background.js'),'utf8'),{chrome,fetch,AbortController,TextDecoder});connect(port);
 return {sent,send:msg=>message(msg),disconnect:()=>{port.closed=true;disconnect()}};
}
const tick=()=>new Promise(r=>setImmediate(r));
test('streams a complete reply',async()=>{const s=setup(async()=>new Response('data: {"type":"text","delta":"Hello"}\n\ndata: {"type":"done"}\n\n'));s.send({type:'chat',session:'test',message:'test'});await tick();assert.deepEqual(s.sent.map(e=>e.type),['text','done','stream-end']);});
test('disconnect aborts a pending request without posting to closed port',async()=>{let signal;const s=setup((url,opts)=>{signal=opts.signal;return new Promise((resolve,reject)=>signal.addEventListener('abort',()=>reject(Object.assign(Error('aborted'),{name:'AbortError'}))));});s.send({type:'chat',session:'test',message:'test'});s.disconnect();await tick();assert.equal(signal.aborted,true);assert.equal(s.sent.length,0);});
test('network failures after disconnect do not throw while sending error or final event',async()=>{let rejectFetch;const s=setup(()=>new Promise((resolve,reject)=>rejectFetch=reject));s.send({type:'chat',session:'test',message:'test'});s.disconnect();rejectFetch(Error('offline'));await tick();assert.equal(s.sent.length,0);});
test('failed reset is reported as error, not success',async()=>{const s=setup(async()=>new Response('',{status:500}));s.send({type:'reset',session:'test'});await tick();assert.deepEqual(s.sent.map(e=>e.type),['error']);});
