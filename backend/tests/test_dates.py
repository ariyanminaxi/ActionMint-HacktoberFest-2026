from app.meetings.dates import resolve_due_date

def test_day_first_absolute_and_relative_dates():
    base='2026-10-26'
    assert resolve_due_date('30/10',base)==('2026-10-30',False)
    assert resolve_due_date('by Friday',base)==('2026-10-30',True)
    assert resolve_due_date('next Tuesday',base)==('2026-11-03',True)
    assert resolve_due_date('early next week',base)==(None,False)
    assert resolve_due_date('in 2 weeks',base)==('2026-11-09',True)

def test_absolute_month_date_rolls_forward_when_missing_year():
    assert resolve_due_date('Nov 4th','2026-10-26')==('2026-11-04',False)
