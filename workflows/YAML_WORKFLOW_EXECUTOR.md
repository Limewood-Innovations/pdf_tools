# YAML Workflow Executor

## Overview

The YAML workflow executor is a Python script that runs workflow definitions written in YAML format. It provides variable substitution, dependency management, conditional execution, and error handling for automating multi-step processes.

## What It Does

1. **Loads YAML Workflows** - Parses workflow definition files
2. **Substitutes Variables** - Environment variables and custom variables
3. **Manages Dependencies** - Ensures steps run in correct order
4. **Handles Errors** - Stop or continue based on configuration
5. **Executes Steps** - Runs Python scripts defined in workflow

## Usage

### Basic Execution

```bash
python workflows/run_workflow.py path/to/workflow.yaml
```

### With Custom Variables

```bash
python workflows/run_workflow.py workflow.yaml \
    --var input_pdf=document.pdf \
    --var output_dir=./results
```

### Dry Run (Preview)

```bash
python workflows/run_workflow.py workflow.yaml --dry-run
```

## CLI Options

| Option | Description |
|--------|-------------|
| `workflow_file` | Path to YAML workflow file (required) |
| `--var KEY=VALUE` | Set workflow variable (repeatable) |
| `--dry-run` | Show what would execute without running |

## YAML Workflow Format

### Basic Structure

```yaml
name: Workflow Name
description: What this workflow does
version: "1.0"

variables:
  input_dir: "./01_input"
  output_dir: "./02_output"

steps:
  - name: "Step Name"
    description: "What this step does"
    tool: "module.function"
    script: |
      Python code to execute
    depends_on: []
    outputs: []
    condition: "${ENABLED}"
    on_error: "stop"

post_workflow:
  - name: "Cleanup"
    script: |
      Final cleanup code
```

### Example Workflow

```yaml
name: PDF Processing Pipeline
description: Split, clean, and normalize PDFs

variables:
  input_dir: "${INPUT_DIR:-./01_input}"
  split_dir: "./02_split"
  normalized_dir: "./03_normalized"

steps:
  - name: "Split PDFs"
    description: "Split all PDFs into 2-page chunks"
    tool: "tools.split_pages"
    script: |
      from tools.split_pages import split_every_n_pages
      from pathlib import Path
      
      for pdf in Path("${input_dir}").glob("*.pdf"):
          split_every_n_pages(pdf, Path("${split_dir}"), n=2)
    outputs:
      - split_files
    on_error: "stop"
    
  - name: "Normalize PDFs"
    description: "Optimize PDFs with Ghostscript"
    depends_on: ["Split PDFs"]
    script: |
      import subprocess
      from pathlib import Path
      
      for pdf in Path("${split_dir}").glob("*.pdf"):
          output = Path("${normalized_dir}") / pdf.name
          subprocess.run([
              "gs", "-sDEVICE=pdfwrite",
              "-dCompatibilityLevel=1.4",
              "-dPDFSETTINGS=/printer",
              "-dNOPAUSE", "-dQUIET", "-dBATCH",
              f"-sOutputFile={output}",
              str(pdf)
          ])
    depends_on: ["Split PDFs"]
    on_error: "continue"

post_workflow:
  - name: "Summary"
    script: |
      print("Workflow completed successfully")
```

## Variable Substitution

### Environment Variables

```yaml
variables:
  # Direct substitution
  api_url: "${API_URL}"
  
  # With default value
  model: "${OLLAMA_MODEL:-gpt-oss:20b}"
  
  # Conditional (use "true" if var is set)
  feature_enabled: "${FEATURE_FLAG:+true}"
```

### Workflow Variables

```yaml
variables:
  input: "./data"
  output: "./results"

steps:
  - script: |
      process_files("${input}", "${output}")
```

### CLI Variables

```bash
# Override workflow variables
python workflows/run_workflow.py workflow.yaml \
    --var input=/custom/path \
    --var output=/other/path
```

## Step Configuration

### Dependencies

```yaml
steps:
  - name: "Download"
    script: ...
    
  - name: "Process"
    depends_on: ["Download"]  # Waits for Download
    script: ...
```

### Error Handling

```yaml
steps:
  - name: "Critical Operation"
    on_error: "stop"      # Stop workflow on error
    script: ...
    
  - name: "Optional Step"
    on_error: "continue"  # Continue even if fails
    script: ...
```

### Conditional Execution

```yaml
steps:
  - name: "Upload to Cloud"
    condition: "${UPLOAD_ENABLED}"  # Only runs if true
    script: ...
```

### Output Passing

```yaml
steps:
  - name: "Load Data"
    script: |
      data = load_data()
      results = []
    outputs:
      - data
      - results
      
  - name: "Process Data"
    depends_on: ["Load Data"]
    script: |
      # 'data' and 'results' available from previous step
      for item in data:
          results.append(process(item))
```

## Output

### Dry Run
```
============================================================
Workflow: PDF Processing Pipeline
Description: Split, clean, and normalize PDFs
============================================================

[DRY RUN MODE - No actual execution]

[1] Split PDFs
    Split all PDFs into 2-page chunks
    Script:
      from tools.split_pages import split_every_n_pages
      ...

[2] Normalize PDFs
    Optimize PDFs with Ghostscript
    Script:
      import subprocess
      ...

============================================================
Workflow completed: 2/2 steps
============================================================
```

### Execution
```
============================================================
Workflow: PDF Processing Pipeline
...
============================================================

[1] Split PDFs
    Split all PDFs into 2-page chunks
    ✓ Completed

[2] Normalize PDFs
    Optimize PDFs with Ghostscript
    ✓ Completed

[POST] Summary
Workflow completed successfully

============================================================
Workflow completed: 2/2 steps
============================================================
```

## Dependencies

```bash
pip install pyyaml
```

## Examples

### Example 1: Simple File Processing

**workflow.yaml:**
```yaml
name: File Copy
variables:
  source: "./input"
  dest: "./output"

steps:
  - name: "Copy Files"
    script: |
      import shutil
      from pathlib import Path
      
      Path("${dest}").mkdir(exist_ok=True)
      for file in Path("${source}").glob("*"):
          shutil.copy(file, "${dest}")
```

**Run:**
```bash
python workflows/run_workflow.py workflow.yaml
```

### Example 2: Multi-Step with Dependencies

**pipeline.yaml:**
```yaml
name: Data Pipeline
steps:
  - name: "Extract"
    script: |
      data = extract_data()
    outputs: [data]
    
  - name: "Transform"
    depends_on: ["Extract"]
    script: |
      transformed = transform(data)
    outputs: [transformed]
    
  - name: "Load"
    depends_on: ["Transform"]
    script: |
      load_data(transformed)
```

### Example 3: Conditional Steps

**deploy.yaml:**
```yaml
name: Deployment
variables:
  deploy_prod: "${DEPLOY_PROD:+true}"

steps:
  - name: "Test"
    script: |
      run_tests()
    
  - name: "Deploy to Production"
    condition: "${deploy_prod}"
    depends_on: ["Test"]
    script: |
      deploy_to_production()
```

**Run with condition:**
```bash
DEPLOY_PROD=yes python workflows/run_workflow.py deploy.yaml
```

## Troubleshooting

### Variable Not Substituting

Check variable definition:
```bash
python workflows/run_workflow.py workflow.yaml --var myvar=value
```

### Step Skipped

Check:
- Dependencies are met
- Condition evaluates to true
- Previous steps completed

### Import Errors

Ensure Python path includes project root:
```bash
export PYTHONPATH=$PWD:$PYTHONPATH
python workflows/run_workflow.py workflow.yaml
```

### Script Errors

Use `--dry-run` to validate syntax:
```bash
python workflows/run_workflow.py workflow.yaml --dry-run
```

## Advanced Features

### Error Recovery

```yaml
steps:
  - name: "Risky Operation"
    on_error: "continue"
    script: |
      try:
          risky_operation()
      except Exception as e:
          log_error(e)
          # Continue with degraded functionality
```

### Dynamic Workflows

```yaml
steps:
  - name: "Process Files"
    script: |
      from pathlib import Path
      
      files = list(Path("${input_dir}").glob("*.pdf"))
      for i, file in enumerate(files):
          print(f"Processing {i+1}/{len(files)}: {file}")
          process_file(file)
```

## Related Files

- [YAML_WORKFLOW_GUIDE.md](../YAML_WORKFLOW_GUIDE.md) - Complete workflow syntax guide
- [.agent/workflows/pdf-batch-workflow.md](../.agent/workflows/pdf-batch-workflow.md) - Example workflow definition
