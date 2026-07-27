"""Shared configuration for the uketsuke program."""


configuration = {
    "host-os-functionality": {
        "read-file": None,
        "write-and-sync": None,
        "copy-and-sync": None,
        "delete-and-sync": None,
    },
    "host-functions": {
        "characterize-job": None,
        "dispatch-job": None,
    },
    "directories": {
        "inbox": None,
        "work-space": None,
    },
}


def initialize_configuration_at_startup_time(new_configuration):
    configuration.clear()
    configuration.update(new_configuration)
    validate_that_all_expected_configuration_keys_are_present()


def validate_that_all_expected_configuration_keys_are_present():
    expected = {
        "host-os-functionality": {
            "read-file",
            "write-and-sync",
            "copy-and-sync",
            "delete-and-sync",
        },
        "host-functions": {
            "characterize-job",
            "dispatch-job",
        },
        "directories": {
            "inbox",
            "work-space",
        },
    }

    for section, expected_keys in expected.items():
        if section not in configuration:
            raise ValueError(f"Missing configuration section: {section}")

        for key in expected_keys:
            if key not in configuration[section]:
                raise ValueError(f"Missing configuration value: {section}.{key}")
