import asyncio
import json

from educational_engine.streaming_handler import StreamingResponseHandler


def test_stream_response_phases_order():
    synthesized = {
        'answer': 'Recursion is a function calling itself.',
        'teaching_answer': "Here's a teaching-style explanation.",
        'analogies': ['nested boxes'],
        'examples': ['A folder containing folders'],
        'visual_explanation': 'viz',
        'diagram_type': 'text_structure',
        'has_flowchart': False,
        'has_comparison_table': False,
        'key_concepts': ['Recursion'],
        'key_takeaways': ['Takeaway 1', 'Takeaway 2'],
        'prerequisites': [],
        'related_concepts': [],
        'follow_up_suggestions': ['What is a base case?'],
        'difficulty_level': 'beginner',
        'beginner_answer': 'Beginner version',
        'advanced_answer': 'Advanced version',
        'citations': [],
        'sources': [],
        'clarity_score': 0.5,
        'completeness_score': 0.5,
        'learning_value': 0.5
    }

    async def collect_phases():
        gen = StreamingResponseHandler.stream_response(synthesized, request_id='r1')
        phases = []
        async for chunk in gen:
            obj = json.loads(chunk)
            phases.append(obj.get('phase'))
        return phases

    phases = asyncio.run(collect_phases())
    assert phases == ['initial', 'teaching', 'visual', 'takeaways', 'followup', 'complete']
