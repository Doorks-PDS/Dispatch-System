from fastapi import HTTPException
from app.routers.doorks_operations import calculate, Timecard, hours, money

def test_daily_overtime():
    card=Timecard(employee_id='e',work_date='2026-11-03',time_in='8:00 AM',time_out='5:30 PM',lunch_minutes=30)
    result=calculate(card)
    assert result['regular_hours']==8
    assert result['overtime_hours']==1

def test_overnight_shift():
    card=Timecard(employee_id='e',work_date='2026-11-03',time_in='8:00 PM',time_out='2:00 AM',lunch_minutes=30)
    assert calculate(card)['actual_hours']==5.5

def test_invalid_lunch():
    card=Timecard(employee_id='e',work_date='2026-11-03',time_in='9:00 AM',time_out='9:15 AM',lunch_minutes=60)
    try:calculate(card)
    except HTTPException as e:assert e.status_code==400
    else:raise AssertionError('invalid lunch accepted')

def test_money_rejects_negative():
    try:money(-1)
    except HTTPException as e:assert e.status_code==400
    else:raise AssertionError('negative amount accepted')
