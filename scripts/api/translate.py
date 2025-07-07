import json
import logging
import os
import pandas as pd
from tqdm import tqdm
from google.cloud import translate_v2 as translate
from scripts.csv_columns import ADDRESS, TRANSLATED
from settings import TRANSLATIONS

''' Runs asynchronous Translate requests to a Google Translate API Wrapper in Python '''

logging.info(os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))

MAX_SEGMENTS = 128
MAX_BYTES = 70_000

translator = translate.Client()


def is_non_english_string(string: str) -> bool:
    ''' 
    Returns True if all characters in the string are NOT ASCII excluding "›" delimiters 
    Note that this only refers to character sets and not the actual language used
    '''
    return "›" not in string and not string.isascii()


def chunk_segments_and_bytes(strings, max_segments=MAX_SEGMENTS, max_bytes=MAX_BYTES):
    """
    Splits strings into batches to comply with Google Cloud Translate rate limits.
    Google Cloud Translate imposes two constraints when sending batch translation requests:
    1. A maximum number of segments (strings) (128).
    2. A maximum byte size per request (70,000 bytes).
    """
    batch = []
    batch_size = 0
    for s in strings:
        s_bytes = len(json.dumps(s, ensure_ascii=False).encode('utf-8'))
        if s_bytes > max_bytes:
            yield [s]
            continue
        if len(batch) >= max_segments or batch_size + s_bytes > max_bytes:
            yield batch
            batch = [s]
            batch_size = s_bytes
        else:
            batch.append(s)
            batch_size += s_bytes
    if batch:
        yield batch


def batch_translate(strings: list[str], target='en') -> list[str]:
    ''' 
    Translates a batch of strings to the target language using Google Cloud Translate. 
    Which allows for a maximum of 128 segments (strings) and a maximum byte size of 70,000 bytes per batch.
    This significantly reduces the number of API calls and speeds up the translation process.
    If the translation fails, it returns errors and their reason for each string.

    '''
    try:
        results = translator.translate(strings, target_language=target)
        return [res['translatedText'] for res in results]
    
    except Exception as e:
        errors = [f"[TRANSLATION_FAILED: {str(e)}]" for _ in strings]
        logging.debug(errors)
        return errors


def translate_series(
    series: pd.Series,
    target: str = 'en',
) -> pd.Series:
    """
    Translates all strings in a pandas "string" Series into a target language (default is English).
    Returns a Series of translations, preserving the row order indices.
    """
    series = series.astype("string")
    candidates: list[str] = [s for s in series if pd.notna(s) and is_non_english_string(s)]
    progress = tqdm(total=len(series), desc="Translating", position=0)

    mapping: dict[str, str] = {}
    for batch in chunk_segments_and_bytes(candidates):
        translated: list[str] = batch_translate(batch, target)
        mapping.update(zip(batch, translated))

    translated = series.map(lambda s: mapping.get(s, s) if pd.notna(s) else s)

    progress.update(len(translated))
    progress.close()

    return translated


def load_translations(df: pd.DataFrame) -> pd.DataFrame:
    '''
    Translates addresses to English using Google Translate.
    Loads from CSV if the file already exists.
    '''
    if TRANSLATIONS.exists() and not os.getenv("ALWAYS_TRANSLATE") == "True":
        logging.info(f"Returned existing translations.")
        return pd.read_csv(TRANSLATIONS, encoding="utf-8-sig")
    else:
        df[TRANSLATED] = translate_series(df[ADDRESS])
        df.to_csv(TRANSLATIONS, index=False, encoding="utf-8-sig")
        return df



if __name__ == "__main__":

    from scripts.load import load_raw_datasets
    from scripts.process import merge_on_unique

    # python -m scripts.api.translate
    os.environ["ALWAYS_TRANSLATE"] = "True"
    training, testing = load_raw_datasets()
    unique_addresses: pd.DataFrame = (merge_on_unique([training[ADDRESS], testing[ADDRESS]]).astype(str).to_frame(name=ADDRESS).reset_index(drop=True))
    unique_addresses = unique_addresses.head(1)
    load_translations(unique_addresses)


