import warnings

def load_params_from_class(instance):
    """
    Initialize instance attributes from merged PARAM_SPECS
    across the inheritance chain.

    Each PARAM_SPECS entry: { name: {"default": ..., "type": ..., "desc": ...} }
    """
    cls = instance.__class__
    print(f"⚙️ Loading default parameters for {cls.__name__}...")

    # --- Merge PARAM_SPECS from all bases (Base → Derived) ---
    merged_specs = {}
    for base in reversed(cls.__mro__):
        if hasattr(base, "PARAM_SPECS"):
            merged_specs.update(base.PARAM_SPECS)

    # --- Apply defaults ---
    for name, spec in merged_specs.items():
        val = spec.get("default", None)
        setattr(instance, name, val)
        print(f"   • {name:<20} ← {val} (default)")

def load_params_from_config(instance, config):
    if not hasattr(config, "params") or not isinstance(config.params, dict):
        print(f"⚙️ No config.params found for {instance.__class__.__name__} → using defaults.")
        return

    cls = instance.__class__
    params = {k.lower(): v for k, v in config.params.items()}  # normalize
    print(f"⚙️ Loading overrides from config.params for {cls.__name__}...")

    merged_specs = {}
    for base in reversed(cls.__mro__):
        if hasattr(base, "PARAM_SPECS"):
            merged_specs.update(base.PARAM_SPECS)

    for name, spec in merged_specs.items():
        aliases = [name.lower()] + [a.lower() for a in spec.get("aliases", [])]
        for key in aliases:
            if key in params:
                val = params[key]
                expected_type = spec.get("type", None)
                if expected_type:
                    try:
                        val = expected_type(val)
                    except Exception:
                        pass
                setattr(instance, name, val)
                print(f"   ✅ {name:<20} overridden ← {val} (from '{key}')")
                break



