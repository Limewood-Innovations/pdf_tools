# YAML Workflow Guide

## Overview

This guide explains how to create and execute YAML-based workflows for PDF processing pipelines.

## Workflow Structure

A YAML workflow consists of:

```yaml
name: Workflow Name
description: What this workflow does
version: "1.0"

variables:
  key: value

steps:
  - name: Step Name
    description: What this step does
    tool: module.function
    script: |
      Python code to execute
    depends_on: []
    outputs: []
    on_error: "stop"

post_workflow:
  - name: Cleanup
    script: |
      Final steps
```

## Variable Substitution

### Environment Variables

```yaml
variables:
  # Direct substitution
  api_url: "${API_URL}"
  
  # With default value
  model: "${OLLAMA_MODEL:-gpt-oss:20b}"
  
  # Conditional (use "true" if VAR is set)
  enabled: "${FEATURE_ENABLED:+true}"
```

### Workflow Variables

```yaml
variables:
  input_dir: "./01_input"
  output_dir: "./02_output"

steps:
  - name: Process
    script: |
      process_files("${input_dir}", "${output_dir}")
```

## Step Configuration

### Dependencies

```yaml
steps:
  - name: Step A
    script: ...
    
  - name: Step B
    depends_on: ["Step A"]  # Waits for Step A
    script: ...
```

### Error Handling

```yaml
steps:
  - name: Critical Step
    script: ...
    on_error: "stop"      # Stop workflow on error (default)
    
  - name: Optional Step
    script: ...
    on_error: "continue"  # Continue even if this fails
```

### Conditional Execution

```yaml
steps:
  - name: Upload
    condition: "${UPLOAD_ENABLED}"
    script: ...
```

### Outputs

```yaml
steps:
  - name: Extract
    script: |
      files = extract_files()
    outputs:
      - files  # Available to subsequent steps
      
  - name: Process
    depends_on: ["Extract"]
    script: |
      for file in files:  # Use output from previous step
          process(file)
```

## Running Workflows

### Command Line

```bash
# Basic execution
python run_workflow.py workflows/my-workflow.yaml

# With variables
python run_workflow.py workflows/my-workflow.yaml \
    --var input_pdf=document.pdf \
    --var output_dir=./results

# Dry run (show what would execute)
python run_workflow.py workflows/my-workflow.yaml --dry-run
```

### Environment Variables

```bash
# Set environment variables
export OLLAMA_URL=http://localhost:11434
export PUSHOVER_USER_KEY=your-key-here

# Run workflow (uses env vars)
python run_workflow.py workflows/iban-extraction.yaml \
    --var input_pdf=loan.pdf
```

## Example Workflows

### PDF Batch Processing

```yaml
name: PDF Batch Processing
variables:
  input_dir: "./01_input"
  split_dir: "./02_processed"
  clean_dir: "./03_cleaned"

steps:
  - name: Split PDFs
    script: |
      from tools.split_pages import split_every_n_pages
      from pathlib import Path
      
      pdfs = list(Path("${input_dir}").glob("*.pdf"))
      for pdf in pdfs:
          split_every_n_pages(pdf, Path("${split_dir}"), n=2)
    outputs:
      - pdfs
      
  - name: Remove Blanks
    depends_on: ["Split PDFs"]
    script: |
      from tools.blank_page import remove_blank_pages
      from pathlib import Path
      
      for part in Path("${split_dir}").glob("*.pdf"):
          dst = Path("${clean_dir}") / part.name
          remove_blank_pages(part, dst)
```

### IBAN Extraction

See [workflows/iban-extraction.yaml](file:///Users/caesium/Documents/dev/02_customer/nhg/pdf_tools/workflows/iban-extraction.yaml) for a complete example.

## Best Practices

### 1. Use Descriptive Names

```yaml
steps:
  # Good
  - name: "Extract text from PDFs using pdfplumber"
    
  # Bad
  - name: "Step 1"
```

### 2. Handle Errors Appropriately

```yaml
steps:
  # Critical step - stop on failure
  - name: Validate Input
    on_error: "stop"
    
  # Optional notification - continue on failure  
  - name: Send Email
    on_error: "continue"
```

### 3. Use Dependencies

```yaml
steps:
  - name: Download
    ...
    
  - name: Process
    depends_on: ["Download"]  # Ensures order
```

### 4. Document Variables

```yaml
# Document what variables are expected
variables:
  # Required: Path to input PDF
  input_pdf: ""
  
  # Optional: Ollama model (default: gpt-oss:20b)
  ollama_model: "${OLLAMA_MODEL:-gpt-oss:20b}"
```

## Troubleshooting

### Variable Not Substituting

Check that the variable is defined:
```bash
python run_workflow.py workflow.yaml --var missing_var=value
```

### Step Skipped

Check dependencies and conditions:
```yaml
- name: My Step
  depends_on: ["Parent Step"]  # Parent must complete first
  condition: "${ENABLED}"       # Variable must be "true"
```

### Import Errors

Ensure tools are on Python path:
```bash
export PYTHONPATH=/path/to/pdf_tools:$PYTHONPATH
python run_workflow.py workflow.yaml
```

## Dependencies

Install required packages:

```bash
pip install pyyaml requests pdfplumber
```

For IBAN extraction workflow, also install:
```bash
pip install requests  # For Ollama API calls
```
