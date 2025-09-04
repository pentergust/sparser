package provider

import "time"

type Lesson struct {
	Name    string
	Cabinet string
}

type DaySchedule map[string][]Lesson
type Schedule []DaySchedule

type ScheduleStatus struct {
	Parsed time.Time `json:"parsed"`
	Hash   string    `json:"hash"`
}

type ScheduleProvider interface {
	Day(day time.Time) (*DaySchedule, error)
	Week() (*Schedule, error)
	Status() ScheduleStatus
}
