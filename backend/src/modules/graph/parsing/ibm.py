import io
from pathlib import Path

import pandas as pd

__all__ = [
    'IBM_REQUIRED_COLUMNS',
    'normalize_ibm_transactions',
    'read_ibm_transactions',
]

IBM_REQUIRED_COLUMNS = [
    'Timestamp',
    'From Bank',
    'Account',
    'To Bank',
    'Account.1',
    'Amount Received',
    'Receiving Currency',
    'Amount Paid',
    'Payment Currency',
    'Payment Format',
    'Is Laundering',
]

_KEY_COLUMNS = [
    'Timestamp',
    'From Bank',
    'Account',
    'To Bank',
    'Account.1',
    'Amount Received',
    'Amount Paid',
    'Is Laundering',
]


def _validate_columns(df: pd.DataFrame) -> None:
    missing = [col for col in IBM_REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f'Missing IBM columns: {", ".join(missing)}')


def _validate_not_empty(df: pd.DataFrame) -> None:
    for col in _KEY_COLUMNS:
        values = df[col]
        empty = values.isna() | values.astype(str).str.strip().eq('')
        if bool(empty.any()):
            row_numbers = [str(i) for i in df.index[empty].tolist()]
            raise ValueError(f'Empty values in IBM column {col}: rows {", ".join(row_numbers)}')


def _parse_amounts(values: pd.Series, column: str) -> pd.Series:
    cleaned = values.astype(str).str.replace(',', '', regex=False).str.strip()
    parsed = pd.to_numeric(cleaned, errors='coerce')
    if bool(parsed.isna().any()):
        row_numbers = [str(i) for i in values.index[parsed.isna()].tolist()]
        raise ValueError(
            f'Invalid numeric values in IBM column {column}: rows {", ".join(row_numbers)}',
        )
    return parsed.astype(float)


def _parse_timestamps(values: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(values, errors='coerce', format='mixed')
    if bool(parsed.isna().any()):
        row_numbers = [str(i) for i in values.index[parsed.isna()].tolist()]
        raise ValueError(f'Invalid Timestamp values: rows {", ".join(row_numbers)}')
    return parsed


def _parse_is_laundering(values: pd.Series) -> pd.Series:
    parsed = pd.to_numeric(values, errors='coerce')
    invalid = parsed.isna() | ~parsed.isin([0, 1])
    if bool(invalid.any()):
        row_numbers = [str(i) for i in values.index[invalid].tolist()]
        raise ValueError(f'Invalid Is Laundering values: rows {", ".join(row_numbers)}')
    return parsed.astype(int)


def normalize_ibm_transactions(df: pd.DataFrame) -> pd.DataFrame:
    """Проверяет и нормализирует транзакции IBM для строк AML."""
    _validate_columns(df)
    _validate_not_empty(df)

    timestamps = _parse_timestamps(df['Timestamp'])
    amount_paid = _parse_amounts(df['Amount Paid'], 'Amount Paid')
    amount_received = _parse_amounts(df['Amount Received'], 'Amount Received')
    is_laundering = _parse_is_laundering(df['Is Laundering'])

    return pd.DataFrame(
        {
            'transaction_id': [f'tx_{i}' for i in range(len(df))],
            'timestamp': timestamps,
            'sender_id': df['From Bank'].astype(str).str.strip()
            + ':'
            + df['Account'].astype(str).str.strip(),
            'receiver_id': df['To Bank'].astype(str).str.strip()
            + ':'
            + df['Account.1'].astype(str).str.strip(),
            'amount': amount_paid,
            'amount_received': amount_received,
            'receiving_currency': df['Receiving Currency'].astype(str).str.strip(),
            'payment_currency': df['Payment Currency'].astype(str).str.strip(),
            'payment_format': df['Payment Format'].astype(str).str.strip(),
            'is_laundering': is_laundering,
        },
    )


def read_ibm_transactions(file_bytes: bytes, filename: str | None = None) -> pd.DataFrame:
    """Считывает CSV-файл IBM и возвращает нормализованные транзакции."""
    suffix = Path(filename or '').suffix.lower()

    if suffix in {'.xlsx', '.xls'}:
        raise ValueError('Excel upload is not enabled; upload IBM data as CSV')

    buffer = io.BytesIO(file_bytes)
    df = pd.read_csv(buffer)

    return normalize_ibm_transactions(df)
