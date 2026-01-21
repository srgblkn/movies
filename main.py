# main.py
from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd
import streamlit as st


# --- Настройки ---
DEFAULT_CSV_NAME = "movies.csv"
BASE_URL = "https://ithinker.ru"  # нужно для относительных ссылок вида "/film/..."


def _abs_url(url: Optional[str], base: str = BASE_URL) -> str:
    """Приводит относительные ссылки к абсолютным (если возможно)."""
    if url is None:
        return ""
    u = str(url).strip()
    if not u or u.lower() == "nan":
        return ""
    if u.startswith("http://") or u.startswith("https://"):
        return u
    if u.startswith("//"):
        return "https:" + u
    if u.startswith("/"):
        return base.rstrip("/") + u
    return base.rstrip("/") + "/" + u.lstrip("/")


def _find_csv_path() -> Path:
    """Ищет CSV рядом со скриптом: сначала movies.csv, иначе первый *.csv."""
    here = Path(__file__).resolve().parent
    preferred = here / DEFAULT_CSV_NAME
    if preferred.exists():
        return preferred

    csv_files = sorted(here.glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(
            f"Не найден CSV. Положите файл рядом с main.py и назовите его '{DEFAULT_CSV_NAME}' "
            f"или оставьте любой '*.csv' в этой папке."
        )
    return csv_files[0]


@st.cache_data(show_spinner=False)
def load_movies() -> pd.DataFrame:
    path = _find_csv_path()
    df = pd.read_csv(path, encoding="utf-8")

    required = {"page_url", "image_url", "movie_title", "description"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(
            f"В CSV не хватает колонок: {sorted(missing)}. "
            f"Ожидаемая структура: page_url, image_url, movie_title, description."
        )

    # Нормализуем NaN и ссылки
    df["movie_title"] = df["movie_title"].astype(str).fillna("").str.strip()
    df["description"] = df["description"].astype(str).fillna("").str.strip()
    df["page_url"] = df["page_url"].apply(_abs_url)
    df["image_url"] = df["image_url"].apply(_abs_url)

    # Выкинем пустые строки (на всякий случай)
    df = df[(df["movie_title"] != "") & (df["description"] != "")]
    df = df.reset_index(drop=True)
    return df


def main() -> None:
    st.set_page_config(page_title="Умный поиск фильмов", layout="wide")

    st.title("Умный поиск фильмов")
    st.caption("Демо релиза 1.0: случайные позиции из датасета (название — описание).")

    try:
        df = load_movies()
    except Exception as e:
        st.error(f"Ошибка загрузки CSV: {e}")
        st.stop()

    if df.empty:
        st.warning("В CSV нет строк с непустыми movie_title и description.")
        st.stop()

    col_a, col_b, col_c = st.columns([1, 1, 2])
    with col_a:
        n = st.slider("Сколько фильмов показать", min_value=1, max_value=50, value=10, step=1)
    with col_b:
        refresh = st.button("Показать другие", use_container_width=True)
    with col_c:
        st.write(f"Всего фильмов в CSV: **{len(df)}**")

    # seed в session_state, чтобы обновлять по кнопке
    if "seed" not in st.session_state:
        st.session_state.seed = 42
    if refresh:
        st.session_state.seed += 1

    sample_n = min(n, len(df))
    sample = df.sample(n=sample_n, random_state=st.session_state.seed)

    st.divider()

    for _, row in sample.iterrows():
        title = row["movie_title"]
        desc = row["description"]
        img = row.get("image_url", "")
        page = row.get("page_url", "")

        # Карточка
        with st.container(border=True):
            left, right = st.columns([1, 4], vertical_alignment="top")

            with left:
                if isinstance(img, str) and img.strip():
                    st.image(img, use_container_width=True)
                else:
                    st.caption("Постер отсутствует")

            with right:
                st.subheader(title)
                st.write(desc)

                # Источник — необязательное, но полезное дополнение
                if isinstance(page, str) and page.strip():
                    st.markdown(f"[Перейти на страницу-источник]({page})")

    st.divider()
    st.caption("Далее (в релизах 2.0+): поиск по пользовательскому описанию и выдача top-K по релевантности.")


if __name__ == "__main__":
    main()
