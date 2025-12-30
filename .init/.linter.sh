#!/bin/bash
cd /home/kavia/workspace/code-generation/ecommerce-starter-scaffold-18595-18611/backend
source venv/bin/activate
flake8 .
LINT_EXIT_CODE=$?
if [ $LINT_EXIT_CODE -ne 0 ]; then
  exit 1
fi

