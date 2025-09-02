// Статистика

package handlers

import "github.com/gofiber/fiber/v3"

type StatusHandlers struct{}

type status struct {
	Name    string `json:"name"`
	Version string `json:"version"`
	Service string `json:"service"`
}

func (h StatusHandlers) GetStatus(c fiber.Ctx) error {
	return c.JSON(status{
		Name:    "SParser",
		Version: "v2.0",
		Service: "Google tables",
	})
}
