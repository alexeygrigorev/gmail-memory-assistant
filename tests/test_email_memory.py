"""Check memory isolation, replacement, and streamed failures without API calls."""

import asyncio
import json
import unittest
from unittest.mock import MagicMock, patch

import agent
import memory
import server
from pydantic_ai.messages import (
    FunctionToolCallEvent,
    FunctionToolResultEvent,
    ToolCallPart,
    ToolReturnPart,
)


class MemoryTests(unittest.TestCase):
    def test_disabled_session_does_not_read_or_write_memory(self):
        with patch.object(memory, 'recall', side_effect=AssertionError('read')):
            session = agent.Session(memory_enabled=False)
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
            session = agent.Session()
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
        events = [event async for event in agent.tool_events(stream())]
        self.assertEqual([event['call_id'] for event in events],
                         ['length-call', 'tone-call', 'length-call', 'tone-call'])


if __name__ == '__main__':
    unittest.main()
