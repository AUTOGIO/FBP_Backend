# NFA Module Overview

## Introduction

The NFA (Nota Fiscal Avulsa) module provides automation for creating Brazilian tax invoices (NFAs) through the ATF (Ambiente de Testes Fiscais) system of SEFAZ-PB.

## Architecture

The module is organized into several components:

- **ATF Integration**: Login, frame navigation, selectors
- **Form Fillers**: Individual form section fillers (emitente, destinatario, endereco, produto)
- **Data Validation**: CPF, CNPJ, CEP, phone validation
- **Batch Processing**: Batch NFA creation with retry logic
- **Services**: High-level orchestration

## Module Structure

```
app/modules/nfa/
├── __init__.py              # Module exports
├── atf_selectors.py         # CSS selectors for ATF forms
├── atf_frames.py            # Frame navigation utilities
├── atf_login.py             # ATF authentication
├── emitente_filler.py       # Emitente (issuer) form filler
├── destinatario_filler.py   # Destinatario (recipient) form filler
├── endereco_filler.py       # Address form filler
├── produto_filler.py        # Product/item form filler
├── form_filler.py           # Main form orchestrator
├── data_validator.py        # Data validation utilities
└── batch_processor.py      # Batch processing handler
```

## Key Features

- **Frame-based Navigation**: Handles ATF's frame-based interface
- **Retry Logic**: Automatic retry on failures
- **Data Validation**: Validates CPF, CNPJ, CEP, phone numbers
- **Batch Processing**: Process multiple NFAs efficiently
- **Error Handling**: Comprehensive error handling and logging

## Usage

### Single NFA Creation

```python
from app.modules.nfa import fill_nfa_form_complete

form_data = {
    "emitente_cnpj": "12345678000190",
    "destinatario_doc": "12345678900",
    "endereco": {...},
    "item": {...}
}

success = await fill_nfa_form_complete(page, form_data)
```

### Batch Processing

```python
from app.modules.nfa import BatchNFAProcessor

processor = BatchNFAProcessor(config={...})
results = await processor.process_batch(form_data_list, credentials={...})
```

## Configuration

Configuration is passed via `config` dictionary:

```python
config = {
    "browser": {
        "headless": False,
        "viewport": {"width": 1920, "height": 1080}
    },
    "cdp": {
        "enabled": True,
        "url": "http://localhost:9222"
    },
    "retry": {
        "max_attempts": 3,
        "delay": 2000
    },
    "timeouts": {
        "navigation": 30000,
        "element_wait": 10000
    }
}
```

## Security

- Credentials stored in environment variables or config (never hard-coded)
- No credential leaks in logs
- Structured logging for all operations

