from educational_engine.streamlit_helpers import format_teaching_flow_for_display


def test_format_teaching_flow_full():
    teaching = {
        'step_1_intuitive': 'An intuitive explanation',
        'step_2_example': 'A real-world example',
        'step_3_technical': 'Technical details',
        'step_4_how_it_works': 'How it works section',
        'step_5_mistakes': 'Common mistakes',
        'step_6_summary': 'Concise summary',
        'step_7_check': 'Check questions',
        'teaching_strategy': 'analogical',
        'key_takeaways': ['A', 'B'],
        'common_misconceptions': 'Not X'
    }

    out = format_teaching_flow_for_display(teaching)

    assert out['Intuitive explanation'] == 'An intuitive explanation'
    assert out['Real-world example'] == 'A real-world example'
    assert out['Technical explanation'] == 'Technical details'
    assert out['metadata']['teaching_strategy'] == 'analogical'


def test_format_teaching_flow_partial_fallback():
    # Only provide a global teaching_answer and one specific step
    teaching = {
        'teaching_answer': 'Fallback teaching answer',
        'step_3_technical': 'Only technical'
    }

    out = format_teaching_flow_for_display(teaching)

    # Steps without specific keys should use the fallback
    assert out['Intuitive explanation'] == 'Fallback teaching answer'
    assert out['Real-world example'] == 'Fallback teaching answer'
    # Provided step should be preserved
    assert out['Technical explanation'] == 'Only technical'
