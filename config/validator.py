from models.service import Service


class ConfigValidator:
    """Additional configuration validation."""

    @staticmethod
    def validate(services: list[Service]) -> None:
        names = set()

        for service in services:
            if service.name in names:
                raise ValueError(
                    f"Duplicate service name: {service.name}"
                )

            names.add(service.name)