"""Check memory isolation, replacement, and streamed failures without API calls."""

import asyncio
import json
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import agent
import memory
import server
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.messages import (
    FunctionToolCallEvent,
    FunctionToolResultEvent,
    ToolCallPart,
    ToolReturnPart,
    ModelResponse,
    TextPart,
)


class MemoryTests(unittest.TestCase):
    def test_backend_has_no_frontend_build_dependency(self):
        self.assertEqual(server.index(), {'status': 'ok', 'service': 'mem-hub'})
        self.assertNotIn('/assets', [route.path for route in server.app.routes])

    def test_disabled_session_does_not_read_or_write_memory(self):
        with patch.object(memory, 'recall', side_effect=AssertionError('read')):
            session = server.Session(memory_enabled=False)
            session.refresh('Draft a speaker invitation reply')
        self.assertEqual(session.memories, [])
        self.assertEqual(session.agent._function_toolset.tools, {})

    def test_changed_rule_replaces_same_user_category_key(self):
        client = MagicMock()
        with patch.object(memory, 'VectorAIClient') as factory, patch.object(memory, 'embed', return_value=[0.0]):
            factory.return_value.__enter__.return_value = client
            memory.remember('Keep replies under 100 words', 'speaker invitations', 'length')
            first = client.points.upsert.call_args.args[1][0]
            memory.remember('Keep replies under 80 words', 'speaker invitations', 'length')
            updated = client.points.upsert.call_args.args[1][0]
            memory.remember('Keep replies under 80 words', 'sponsor inquiries', 'length')
            other = client.points.upsert.call_args.args[1][0]
        self.assertEqual(first.id, updated.id)
        self.assertNotEqual(first.id, other.id)
        self.assertEqual(updated.payload['content'], 'Keep replies under 80 words')
        self.assertEqual(updated.payload['category'], 'speaker invitations')

    def test_search_uses_current_request(self):
        with patch.object(memory, 'recall', return_value=[]) as recall:
            session = server.Session()
            session.refresh('Reply to the CloudNest sponsor inquiry')
        recall.assert_called_once_with('Reply to the CloudNest sponsor inquiry', limit=8)

    def test_memory_modes_have_separate_conversation_histories(self):
        server.sessions.clear()
        enabled = server.get_session('comparison', True)
        disabled = server.get_session('comparison', False)
        enabled.history.append('previous turn')
        self.assertEqual(disabled.history, [])
        self.assertIsNot(enabled, disabled)
        server.reset_session('comparison')
        self.assertFalse(server.sessions)

    def test_usage_report_excludes_memories_not_available_to_the_agent(self):
        stored = '[speaker invitations] Ask about the audience.'
        ctx = SimpleNamespace(deps=agent.DraftContext({stored}))
        self.assertEqual(agent.report_memory_usage(ctx, [stored, stored]), {'used': [stored]})
        self.assertEqual(agent.report_memory_usage(ctx, [stored, '[general] An invented preference']), {
            'used': [stored], 'unavailable': ['[general] An invented preference'],
        })

    def test_stale_usage_after_memory_reset_does_not_block_the_draft(self):
        calls = 0

        def respond(messages, info):
            nonlocal calls
            calls += 1
            if calls == 1:
                return ModelResponse(parts=[ToolCallPart('report_memory_usage', {
                    'items': ['[speaker invitations] A rule from before the reset'],
                }, 'usage')])
            return ModelResponse(parts=[TextPart('Hi Daniel, thanks for the invitation.')])

        drafting_agent = agent.build_agent([])
        with drafting_agent.override(model=FunctionModel(respond)):
            result = drafting_agent.run_sync('Draft a reply', deps=agent.DraftContext())
        self.assertEqual(calls, 2)
        self.assertEqual(result.output, 'Hi Daniel, thanks for the invitation.')

    def test_usage_report_can_include_additional_search_results(self):
        found = '[general] Keep replies concise.'
        ctx = SimpleNamespace(deps=agent.DraftContext())
        with patch.object(memory, 'recall', return_value=[found]):
            agent.search_memory(ctx, 'reply length')
        self.assertEqual(agent.report_memory_usage(ctx, [found]), {'used': [found]})

    def test_save_updates_request_context(self):
        ctx = SimpleNamespace(deps=agent.DraftContext())
        with patch.object(memory, 'remember') as remember:
            result = agent.save_memory(ctx, 'Keep replies short.', 'general', 'length')
        remember.assert_called_once_with('Keep replies short.', 'general', 'length')
        self.assertIn('[general] Keep replies short.', result)
        self.assertEqual(ctx.deps.available, {'[general] Keep replies short.'})

    def test_request_context_is_replaced_when_memories_are_refreshed(self):
        session = server.Session()
        previous = session.context
        previous.available.add('[general] Old rule')
        with patch.object(memory, 'recall', return_value=['[general] New rule']):
            session.refresh('Draft a reply')
        self.assertIsNot(session.context, previous)
        self.assertEqual(session.context.available, {'[general] New rule'})

    def test_draft_completes_without_validation_retries_or_usage_report(self):
        calls = 0

        def respond(messages, info):
            nonlocal calls
            calls += 1
            return ModelResponse(parts=[TextPart('Hi Maya — thank you.\n- What is the date?')])

        drafting_agent = agent.build_agent([])
        with drafting_agent.override(model=FunctionModel(respond)):
            result = drafting_agent.run_sync('Draft a reply', deps=agent.DraftContext())
        self.assertEqual(calls, 1)
        self.assertEqual(result.output, 'Hi Maya — thank you.\n- What is the date?')


class StreamingTests(unittest.IsolatedAsyncioTestCase):
    async def test_database_failure_is_reported_in_stream(self):
        with patch.object(server, 'get_session', side_effect=RuntimeError('database unavailable')):
            frames = [frame async for frame in server.event_stream('error-test', 'Draft a reply')]
        events = [json.loads(frame.removeprefix('data: ').strip()) for frame in frames]
        self.assertEqual(events[0]['type'], 'start')
        self.assertEqual(events[-1], {'type': 'error', 'message': 'database unavailable'})

    async def test_parallel_tool_results_preserve_call_ids(self):
        async def stream():
            yield FunctionToolCallEvent(ToolCallPart('save_memory', {'content': 'short'}, 'length-call'))
            yield FunctionToolCallEvent(ToolCallPart('save_memory', {'content': 'warm'}, 'tone-call'))
            yield FunctionToolResultEvent(ToolReturnPart('save_memory', 'Saved: short', 'length-call'))
            yield FunctionToolResultEvent(ToolReturnPart('save_memory', 'Saved: warm', 'tone-call'))
        events = [event async for event in server.tool_events(stream())]
        self.assertEqual([event['call_id'] for event in events],
                         ['length-call', 'tone-call', 'length-call', 'tone-call'])


if __name__ == '__main__':
    unittest.main()
