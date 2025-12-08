# NFA Automation Flows

## Overview

This document describes the main automation flows for NFA creation.

## Flow 1: Single NFA Creation

### Steps

1. **Login to ATF**
   - Navigate to ATF login page
   - Fill credentials
   - Wait for main frame

2. **Select Function**
   - Select FIS_1698 function
   - Wait for NFA form

3. **Fill Form Sections**
   - Emitente (issuer)
   - Destinatario (recipient)
   - Endereco (address)
   - Produto (product/item)

4. **Submit Form**
   - Submit NFA
   - Extract NFA number
   - Save documents (DANFE, DAR)

### Code Example

```python
from app.modules.nfa import (
    perform_login,
    select_function_fis_1698,
    fill_nfa_form_complete
)

# Login
await perform_login(page, usuario, senha)
await select_function_fis_1698(page)

# Fill form
form_data = {...}
success = await fill_nfa_form_complete(page, form_data)
```

## Flow 2: Batch NFA Processing

### Steps

1. **Initialize Batch Processor**
   - Load configuration
   - Connect to browser (CDP or new instance)

2. **Login Once**
   - Perform single login for entire batch
   - Select function

3. **Process Each NFA**
   - For each form data:
     - Wait for form ready
     - Fill form sections
     - Submit
     - Extract NFA number
     - Retry on failure (up to max attempts)

4. **Generate Report**
   - Success/failure counts
   - Error details
   - Duration statistics

### Code Example

```python
from app.modules.nfa import BatchNFAProcessor

processor = BatchNFAProcessor(config=config)
results = await processor.process_batch(
    form_data_list,
    credentials={"usuario": "...", "senha": "..."}
)
```

## Flow 3: Data Validation

### Steps

1. **Validate Destinatario**
   - Check required fields
   - Validate CPF format and checksum
   - Validate CEP format
   - Validate phone format
   - Validate UF (state code)

2. **Report Validation Results**
   - Valid records
   - Invalid records with errors
   - Summary statistics

### Code Example

```python
from app.modules.nfa import validate_destinatario

is_valid, errors = validate_destinatario(destinatario_data, index)
```

## Error Handling

### Retry Logic

- Maximum retry attempts: 3 (configurable)
- Exponential backoff between retries
- Error screenshots saved on failure

### Common Errors

- **Frame not found**: Page structure changed
- **Element timeout**: Form loading slowly
- **Validation error**: Invalid data format
- **Network error**: Connection issues

## Performance Considerations

- Batch processing: ~2 seconds delay between NFAs
- Form filling: ~5-10 seconds per NFA
- Total batch time: ~(N * 10) seconds + overhead

