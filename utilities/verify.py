import json
import pandas as pd
import polars as pl


def load_dict_from_json(json_path):
    with open(json_path, "r", encoding="utf-8") as json_file:
        try:
            correct_json = json.load(json_file)
        except json.JSONDecodeError as e:
            print(e)
            correct_json = None
        return correct_json


def verify_df_pairs(
    df,
    make_col="MARCA",
    model_col="MODELLO",
    json_path="/home/python_script/day-by-day/template_make_model.json",
):
    """
    Useful function to automatically correct known database errors that are still not resolved, and also to discover
    new errors. There is a .json file that is used to check each pair found in the dataframe against the .json file
    that contains all the correct pairs. When new pairs are added to the database, they are manually validated
    and added to the .json file.

    Parameters
    ----------
    df : dataframe.
        The dataframe obtained by the SQL query.
    json_path : string.
        The path of the .json file.
    make_col : string, optional.
        The first column for the make of the vehicle. The default is "MARCA".
    model_col : string, optional.
        The second column for the model of the vehicle. The default is "MODELLO".
    json_path : string, optional.
        The json path for the dictionary. Set for the one used by the DR day-by-day script by default to prevent breakage.

    Returns
    -------
    df : dataframe
        Returns the corrected dataframe that will then be converted into csv.

    """
    # df = df.drop(
    #     columns=["data_immatricolazione_del_veicolo", "data_omologazione"]
    # )
    user_input = ""
    while user_input.casefold() != "skip":
        template_dict = load_dict_from_json(json_path)
        if not template_dict:
            print("Json non corretto. Revisionare gli errori.")
            return None
        corrections = {
            ("PEUGEOT", "JUMPER"): ("PEUGEOT", "BOXER"),
            ("CITROEN", "BOXER"): ("CITROEN", "JUMPER"),
            ("CITROEN", "DOBLÒ"): ("CITROEN", "JUMPER"),
            ("RENAULT", "SPRINTER"): ("RENAULT", "MASTER"),
            ("FIAT", "BERLINGO"): ("FIAT", "DOBLÒ"),
            ("FORD", "TRANSPORTER"): ("VOLKSWAGEN", "TRANSPORTER"),
            ("CITROEN", "DUCATO"): ("FIAT", "DUCATO"),
            ("CITROEN", "RIFTER"): ("CITROEN", "BERLINGO"),
            ("DS", "ND"): ("DS", "DS7"),
        }

        corrected_pairs = []
        incorrect_pairs = []
        declared_pairs = set()

        for idx, row in df.iterrows():
            make, model = row[make_col], row[model_col]
            if pd.notna(make) and pd.notna(model):
                # Autocorrect if pair is in corrections list
                if (make, model) in corrections:
                    corrected_make, corrected_model = corrections[
                        (make, model)
                    ]
                    df.at[idx, make_col] = (
                        corrected_make  # Aggiorna il DataFrame
                    )
                    df.at[idx, model_col] = corrected_model
                    corrected_pairs.append(
                        (idx, make, model, corrected_make, corrected_model)
                    )
                # Only save and later show pairs that are not in the dictionary or in corrections.
                elif (
                    make not in template_dict
                    or model not in template_dict[make]
                ):
                    incorrect_pairs.append((idx, make, model))

        if corrected_pairs:
            print("Correzioni applicate:")
        for (
            row_idx,
            old_make,
            old_model,
            new_make,
            new_model,
        ) in corrected_pairs:
            print(
                f"Riga {row_idx}: '{old_make} {old_model}' → '{new_make} {new_model}'"
            )

        if incorrect_pairs:
            for row_idx, make, model in incorrect_pairs:
                if (make, model) not in declared_pairs:
                    print(
                        f"Marca '{make}' - Modello '{model}' non è corretto."
                    )
                    declared_pairs.add((make, model))
            print(declared_pairs)
        else:
            print("Tutte le coppie Marca-Modello sono corrette.")
        return df
    else:
        return None


def verify_df_pairs_polars(
    df,
    make_col="MARCA",
    model_col="MODELLO",
    json_path="/home/python_script/day-by-day/template_make_model.json",
):
    template_dict = load_dict_from_json(json_path)
    if not template_dict:
        print("Json non corretto. Revisionare gli errori.")
        return None

    corrections = {
        ("PEUGEOT", "JUMPER"): ("PEUGEOT", "BOXER"),
        ("CITROEN", "BOXER"): ("CITROEN", "JUMPER"),
        ("CITROEN", "DOBLÒ"): ("CITROEN", "JUMPER"),
        ("RENAULT", "SPRINTER"): ("RENAULT", "MASTER"),
        ("FIAT", "BERLINGO"): ("FIAT", "DOBLÒ"),
        ("FORD", "TRANSPORTER"): ("VOLKSWAGEN", "TRANSPORTER"),
        ("CITROEN", "DUCATO"): ("FIAT", "DUCATO"),
        ("CITROEN", "RIFTER"): ("CITROEN", "BERLINGO"),
        ("DS", "ND"): ("DS", "DS7"),
    }

    # Aggiungi una colonna con il numero di riga (opzionale, solo per la stampa)
    df = df.with_columns(pl.int_range(0, df.height).alias("row_nr"))

    # Crea un DataFrame Polars con le correzioni, usando i nomi delle colonne corrette
    corrections_df = pl.DataFrame(
        {
            make_col: [k[0] for k in corrections.keys()],
            model_col: [k[1] for k in corrections.keys()],
            "corrected_make": [v[0] for v in corrections.values()],
            "corrected_model": [v[1] for v in corrections.values()],
        }
    )

    # Unisci il DataFrame originale con le correzioni
    df_with_corrections = df.join(
        corrections_df,
        on=[make_col, model_col],
        how="left",
    )

    # Applica le correzioni dove necessario
    df = df_with_corrections.with_columns(
        pl.when(pl.col("corrected_make").is_not_null())
        .then(pl.col("corrected_make"))
        .otherwise(pl.col(make_col))
        .alias(make_col),
        pl.when(pl.col("corrected_model").is_not_null())
        .then(pl.col("corrected_model"))
        .otherwise(pl.col(model_col))
        .alias(model_col),
    ).drop(["corrected_make", "corrected_model"])

    # Filtra le righe corrette
    corrected_mask = pl.col("corrected_make").is_not_null()
    corrected_pairs = (
        df_with_corrections.filter(corrected_mask)
        .select(
            pl.col("row_nr"),
            pl.col(make_col).alias("old_make"),
            pl.col(model_col).alias("old_model"),
            pl.col("corrected_make"),
            pl.col("corrected_model"),
        )
        .to_dicts()
    )

    # Trova le coppie non corrette (non nel dizionario)
    incorrect_mask = (~pl.col(make_col).is_in(list(template_dict.keys()))) | (
        ~pl.col(model_col).is_in(
            [m for sublist in template_dict.values() for m in sublist]
        )
    )
    incorrect_pairs = (
        df.filter(incorrect_mask)
        .select(
            pl.col("row_nr"),
            pl.col(make_col),
            pl.col(model_col),
        )
        .to_dicts()
    )

    # Stampa le correzioni applicate
    if corrected_pairs:
        print("Correzioni applicate:")
        for row in corrected_pairs:
            print(
                f"Riga {row['row_nr']}: '{row['old_make']} {row['old_model']}' → '{row['corrected_make']} {row['corrected_model']}'"
            )

    # Stampa le coppie non corrette
    declared_pairs = set()
    if incorrect_pairs:
        for row in incorrect_pairs:
            pair = (row[make_col], row[model_col])
            if pair not in declared_pairs:
                print(
                    f"Marca '{pair[0]}' - Modello '{pair[1]}' non è corretto."
                )
                declared_pairs.add(pair)
        print(declared_pairs)
    else:
        print("Tutte le coppie Marca-Modello sono corrette.")

    return df
