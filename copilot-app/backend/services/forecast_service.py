def compute_forecasts():
    # TODO: remplacer par ML + G4F (P1)
    return {"rows": []}

def get_all_forecasts(cache):
    return cache("forecasts", compute_forecasts, source=["bootstrap"])