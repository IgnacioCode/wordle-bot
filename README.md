# Wordle Bot

This repository contains a small Discord bot that tracks Wordle scores. The
project now includes a basic test suite using `pytest`.

## Running the tests

1. Install the test dependencies (pytest). They are already available in the
   provided environment but can be installed manually with:

   ```bash
   pip install pytest
   ```

2. Execute the tests from the repository root with:

   ```bash
   pytest
   ```

The tests verify the player extraction logic and that score updates work when
processing messages.
