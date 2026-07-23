from educational_engine.master_prompt_engine import MasterPromptEngine


def test_build_tutor_prompt_contains_requirements_and_shape():
    mpe = MasterPromptEngine()
    pedagogical_context = {'question_type': 'definition', 'question_core': 'recursion'}
    strategy_context = {'primary_strategy': 'analogy_first', 'strategy_parameters': {}}

    prompt = mpe._build_tutor_prompt(
        question='What is recursion?',
        answer='Recursion is a function calling itself.',
        pedagogical_context=pedagogical_context,
        strategy_context=strategy_context,
        learner_level='beginner'
    )

    # sanity checks on prompt content
    assert 'TEACHING REQUIREMENTS' in prompt
    assert 'PRIMARY STRATEGY' in prompt
    # ensure the JSON shape keys are present in the instruction block
    assert '"step_1_intuitive"' in prompt
    assert '"step_7_check"' in prompt
