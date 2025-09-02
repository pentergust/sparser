// Расписание уроков

package handlers

import (
	"splatorm/provider"
	"time"

	"github.com/gofiber/fiber/v3"
)

type ScheduleHandlers struct {
	Provider provider.ScheduleProvider
}

func (h ScheduleHandlers) GetDay(c fiber.Ctx) error {
	dateParam := c.Params("date")
	var day time.Time
	var err error
	if dateParam == "" {
		day = time.Now()
	} else {
		day, err = time.Parse(time.DateOnly, dateParam)
		if err != nil {
			return fiber.NewError(404, err.Error())
		}
	}

	res, err := h.Provider.Day(day)
	if err != nil {
		return fiber.NewError(500, err.Error())
	}

	return c.JSON(res)
}

func (h ScheduleHandlers) GetToday(c fiber.Ctx) error {
	res, err := h.Provider.Today()
	if err != nil {
		return fiber.NewError(500, err.Error())
	}

	return c.JSON(res)
}

func (h ScheduleHandlers) GetWeek(c fiber.Ctx) error {
	res, err := h.Provider.Week()
	if err != nil {
		return fiber.NewError(500, err.Error())
	}

	return c.JSON(res)
}

func (h ScheduleHandlers) GetStatus(c fiber.Ctx) error {
	return c.JSON(h.Provider.Status())
}
