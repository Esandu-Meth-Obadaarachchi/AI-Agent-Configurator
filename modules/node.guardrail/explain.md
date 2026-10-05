# Guardrail

## What
Deterministic checks, no model call: redact emails, phone and card numbers, block common prompt-injection phrases, cap length, block terms.

## Why
Cheap, deterministic checks stop obvious abuse and keep personal data out of model calls and logs, without adding latency or cost.

## Trade-off
Pattern checks catch common cases only; determined attackers can phrase around them.
