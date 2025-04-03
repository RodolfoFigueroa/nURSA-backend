import calendar


def format_date(season: str, year: int) -> list[str, str]:
    """Formats a year and season string in a way that's interpretable by Earth Engine's filters.

    Parameters
    ----------
    season: str
        Season of the year to analyze. Possible values are Q1 (spring), Q2 (summer), Q3 (fall), Q4 (winter) and Qall (entire year).

    year: int
        Year to analyze.

    Returns
    -------
    str
        Date string in '{year}-{month}-{day}' format.
    """
    sdict = {
        "Q1": [f"{year}-3-1", f"{year}-5-31"],
        "Q2": [f"{year}-6-1", f"{year}-8-31"],
        "Q3": [f"{year}-9-1", f"{year}-11-30"],
        "Q4": [f"{year}-12-1", f"{year + 1}-2-29"],
        "Qall": [f"{year}-1-1", f"{year}-12-31"],
    }

    return sdict[season]


def season_to_months(season: str) -> tuple[int]:
    """Returns a list of the months corresponding to the given season.

    Parameters
    ----------
    season: str
        Season. Possible values are:
        - `Q1` (spring)
        - `Q2` (summer)
        - `Q3` (fall)
        - `Q4` (winter)
        - `Qall` (entire year)

    Returns
    -------
    list[int]
        List of month indices, starting from 1 (January).
    """
    if season == "Qall":
        return tuple(range(1, 13))
    else:
        season_idx = int(season.replace("Q", ""))
        return tuple(range(3 * (season_idx - 1) + 1, 3 * season_idx + 1))


def get_date_range(month: int, year: int):
    month_str = str(month).rjust(2, "0")
    _, end_day = calendar.monthrange(year, month)
    end_day_str = str(end_day).rjust(2, "0")
    start = f"{year}-{month_str}-01"
    end = f"{year}-{month_str}-{end_day_str}"
    return start, end
