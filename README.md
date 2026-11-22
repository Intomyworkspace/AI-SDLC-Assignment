# AI-SDLC Assignment – Spec-Driven Development & Harness Engineering

A practical implementation of **AI-assisted Software Development Life Cycle (AI-SDLC)** using Spec-Driven Development (SDD), independent validation harnesses, automated testing, and evidence-based engineering.

This repository contains two projects demonstrating how deterministic and AI-powered applications can be developed, tested, evaluated, and validated through structured engineering workflows.

## Project Overview

The assignment is divided into two parts:

| Part | Project | Focus |
|---|---|---|
| Part 1A | Client Short Allocation & Penalty Calculation | Deterministic application and independent validation harness |
| Part 1B | AI-Powered IPO Announcement & Deadline Assistant | AI-based information extraction, validation and evaluation harness |

## Part 1A – Client Short Allocation & Penalty Calculation

### Overview

A Python-based application designed to calculate client short allocation penalties for clearing operations.

The application uses precise Decimal arithmetic to calculate shortfalls, apply grace limits, select penalty slabs, and determine the final penalty amount.

### Key Features

- Reusable Python calculation library.
- Command-Line Interface (CLI).
- Additional local web interface.
- Exact decimal arithmetic using Python's Decimal module.
- Input validation and error handling.
- Deterministic and reproducible results.
- Unit and contract testing.
- Independent validation harness.

### Penalty Slabs

| Net Shortfall | Penalty Rate |
|---|---:|
| Zero | 0.0% |
| Up to ₹1,00,000 (greater than zero) | 0.5% |
| Above ₹1,00,000 up to ₹10,00,000 | 1.0% |
| Above ₹10,00,000 | 5.0% |

### Technology Stack

- Python
- Decimal
- Argparse
- JSON
- HTML
- Pytest
- Ruff
- Bandit