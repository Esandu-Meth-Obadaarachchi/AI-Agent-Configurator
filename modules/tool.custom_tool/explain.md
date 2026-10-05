# Custom tool

## What
For anything without a ready-made block. Describe the tool and its inputs, and Claude writes typed Python that passes a contract test. The code is saved into your spec, so exports stay repeatable.

## Why
Templates can't know your business logic. Describing a tool in words and having Claude write it against a contract test is the fastest safe route.

## Trade-off
Generated code needs review like any other code, even after it passes the contract test.
