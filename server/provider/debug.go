package provider

import "time"

type DebugProvider struct{}

func (p DebugProvider) Day(day time.Time) (*DaySchedule, error) {
	var sc DaySchedule
	sc = make(DaySchedule, 1)
	return &sc, nil
}

func (p DebugProvider) Week() (*Schedule, error) {
	var sc Schedule
	sc = make(Schedule, 1)
	return &sc, nil
}

func (p DebugProvider) Status() ScheduleStatus {
	return ScheduleStatus{
		Parsed: time.Now(),
		Hash:   "hello",
	}
}
