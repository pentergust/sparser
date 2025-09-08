package main

import (
	"splatorm/handlers"
	"splatorm/provider"

	"github.com/gofiber/fiber/v3"
)

func main() {
	app := fiber.New()

	p := provider.LoadFrom("sp_data/")

	// Расписание уроков
	sc := handlers.ScheduleHandlers{
		Provider: provider.DebugProvider{},
	}
	app.Get("/sc/week", sc.GetWeek)
	app.Get("/sc/status", sc.GetStatus)
	app.Get("/sc/:day", sc.GetDay)

	// Общая информация
	status := handlers.StatusHandlers{}
	app.Get("/status", status.GetStatus)

	app.Listen(":4096")
}
