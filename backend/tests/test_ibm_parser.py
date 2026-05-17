import pandas as pd
import pytest

from src.modules.graph.parsing.ibm import normalize_ibm_transactions, read_ibm_transactions


def test_ibm_normalization_success(ibm_df: pd.DataFrame) -> None:
    normalized = normalize_ibm_transactions(ibm_df)

    assert list(normalized.columns) == [
        'transaction_id',
        'timestamp',
        'sender_id',
        'receiver_id',
        'amount',
        'amount_received',
        'receiving_currency',
        'payment_currency',
        'payment_format',
        'is_laundering',
    ]
    assert normalized.loc[0, 'transaction_id'] == 'tx_0'
    assert normalized.loc[0, 'sender_id'] == 'B1:A1'
    assert normalized.loc[0, 'receiver_id'] == 'B2:A2'
    assert normalized.loc[0, 'amount'] == 1000.0
    assert normalized.loc[0, 'is_laundering'] == 1


def test_ibm_missing_required_column(ibm_df: pd.DataFrame) -> None:
    with pytest.raises(ValueError, match='Missing IBM columns'):
        normalize_ibm_transactions(ibm_df.drop(columns=['Amount Paid']))


def test_ibm_invalid_timestamp(ibm_df: pd.DataFrame) -> None:
    ibm_df.loc[0, 'Timestamp'] = 'broken'
    with pytest.raises(ValueError, match='Invalid Timestamp'):
        normalize_ibm_transactions(ibm_df)


def test_ibm_invalid_amount_paid(ibm_df: pd.DataFrame) -> None:
    ibm_df.loc[0, 'Amount Paid'] = 'not-a-number'
    with pytest.raises(ValueError, match='Amount Paid'):
        normalize_ibm_transactions(ibm_df)


def test_ibm_excel_upload_is_not_enabled() -> None:
    with pytest.raises(ValueError, match='Excel upload is not enabled'):
        read_ibm_transactions(b'not-an-excel-file', 'ibm.xlsx')
