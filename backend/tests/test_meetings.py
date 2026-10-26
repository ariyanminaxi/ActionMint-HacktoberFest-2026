from app.meetings.normalize import normalize_transcript
from app.meetings.sample import SAMPLE_TRANSCRIPT, golden_spec
from app.meetings.verify import verify_spec
from app.meetings.questions import parse_questions

def test_sample_normalizes_into_stable_segments():
    segments=normalize_transcript(SAMPLE_TRANSCRIPT)
    assert len(segments)==11
    assert segments[2]['id']=='S3'
    assert segments[2]['speaker']=='Priya'

def test_golden_sample_has_no_guessed_deadlines_or_owner():
    segments=normalize_transcript(SAMPLE_TRANSCRIPT)
    spec=verify_spec(golden_spec('meeting_1234','2026-10-26'),segments)
    assert spec['action_items'][0]['due_iso']=='2026-10-30'
    assert spec['action_items'][1]['due_iso'] is None
    assert spec['action_items'][2]['owner']=='Priya'
    assert spec['action_items'][2]['due_iso'] is None
    assert 'pricing' not in ' '.join(d['text'].lower() for d in spec['decisions'])

def test_question_bank_has_unique_ids_and_rules():
    questions=parse_questions()
    assert {'summary','decisions','actions','open_questions','risks','follow_ups'} <= set(questions)
    ids=[q['id'] for group in questions.values() for q in group]
    assert len(ids)==len(set(ids))
