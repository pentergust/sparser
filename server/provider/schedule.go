package provider

import "time"

type Lesson struct {
	Name    string
	Cabinet string
}

type DaySchedule map[string][]Lesson
type Schedule []DaySchedule

type ScheduleStatus struct {
	Parsed time.Time
	Hash   string
}

type ScheduleProvider interface {
	Day(day time.Time) (*DaySchedule, error)
	Today() (*DaySchedule, error)
	Week() (*Schedule, error)
	Status() ScheduleStatus
}
