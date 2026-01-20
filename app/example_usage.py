#!/usr/bin/env python3
"""
Example usage of test_data_generator for common scenarios.

This script demonstrates how to use the test data generator programmatically
or provides ready-to-run commands for common use cases.
"""

import subprocess
import sys


def run_command(cmd, description):
    """Run a shell command and display output."""
    print(f"\n{'='*70}")
    print(f"SCENARIO: {description}")
    print(f"{'='*70}")
    print(f"Command: {' '.join(cmd)}\n")

    try:
        result = subprocess.run(cmd, check=True, text=True, capture_output=False)
        print(f"\n✓ Success!")
        return result.returncode
    except subprocess.CalledProcessError as e:
        print(f"\n✗ Failed with exit code {e.returncode}", file=sys.stderr)
        return e.returncode
    except KeyboardInterrupt:
        print("\n\n✗ Interrupted by user")
        return 1


def main():
    print("""
╔══════════════════════════════════════════════════════════════════╗
║   WarDragon Analytics - Test Data Generator Examples            ║
╚══════════════════════════════════════════════════════════════════╝

This script demonstrates common usage scenarios for the test data generator.
Choose a scenario or run the commands manually.
    """)

    scenarios = [
        {
            "name": "Quick Test (15 min, 1 kit, 3 drones) - SQL output",
            "cmd": ["python3", "test_data_generator.py", "--mode=sql", "--duration=15m", "--kits=1", "--drones=3"],
            "description": "Small dataset for quick testing. Outputs SQL statements."
        },
        {
            "name": "Quick Test (15 min, 1 kit, 3 drones) - Database",
            "cmd": ["python3", "test_data_generator.py", "--mode=db", "--duration=15m", "--kits=1", "--drones=3"],
            "description": "Small dataset written directly to database."
        },
        {
            "name": "Standard Test (2 hours, 3 kits, 15 drones) - Database",
            "cmd": ["python3", "test_data_generator.py", "--mode=db", "--duration=2h", "--kits=3", "--drones=15"],
            "description": "Standard test scenario matching README defaults."
        },
        {
            "name": "Heavy Activity (1 hour, 5 kits, 20 drones, 60% signals)",
            "cmd": ["python3", "test_data_generator.py", "--mode=db", "--duration=1h", "--kits=5", "--drones=20", "--signal-probability=0.6"],
            "description": "High-activity scenario with many FPV signals."
        },
        {
            "name": "Single Kit Demo (30 min, 1 kit, 5 drones) - SQL to file",
            "cmd": ["bash", "-c", "python3 test_data_generator.py --mode=sql --duration=30m --kits=1 --drones=5 > demo_data.sql"],
            "description": "Generate SQL file for manual import or inspection."
        },
    ]

    # Interactive menu
    while True:
        print("\nAvailable scenarios:\n")
        for i, scenario in enumerate(scenarios, 1):
            print(f"  {i}. {scenario['name']}")
        print(f"  {len(scenarios) + 1}. Show all commands (without running)")
        print("  0. Exit\n")

        try:
            choice = input("Select scenario (0-{}): ".format(len(scenarios) + 1))
            choice = int(choice)

            if choice == 0:
                print("\nExiting.")
                break
            elif choice == len(scenarios) + 1:
                # Show all commands
                print("\n" + "="*70)
                print("ALL COMMANDS")
                print("="*70)
                for i, scenario in enumerate(scenarios, 1):
                    print(f"\n{i}. {scenario['name']}")
                    print(f"   {' '.join(scenario['cmd'])}")
                print()
                continue
            elif 1 <= choice <= len(scenarios):
                scenario = scenarios[choice - 1]
                run_command(scenario['cmd'], scenario['description'])
            else:
                print("Invalid choice. Please try again.")

        except ValueError:
            print("Invalid input. Please enter a number.")
        except KeyboardInterrupt:
            print("\n\nExiting.")
            break


def programmatic_example():
    """Example of using the generator programmatically (as a Python module)."""
    print("""
    # Example: Using test_data_generator as a Python module

    from datetime import timedelta
    from test_data_generator import generate_test_data

    # Generate test data programmatically
    stats = generate_test_data(
        num_kits=3,
        drones_per_kit=15,
        duration=timedelta(hours=2),
        output_mode="db",
        db_url="postgresql://wardragon:wardragon@localhost:5432/wardragon",
        signal_probability=0.3,
    )

    print(f"Generated {stats['drones']} drone records")
    print(f"Generated {stats['signals']} signal records")
    print(f"Generated {stats['health']} health records")
    """)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted. Exiting.")
        sys.exit(0)
