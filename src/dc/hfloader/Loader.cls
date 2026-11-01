Class dc.hfloader.Loader Extends %RegisteredObject
{

ClassMethod Health() As %Status
{
    quit $$$OK
}

ClassMethod Load(dataset As %String = "", split As %String = "train", config As %String = "", target As %String = "", limit As %Integer = 0, revision As %String = "", mode As %String = "replace") As %String [ Language = python ]
{
    import json
    from hfloader import load_to_iris

    result = load_to_iris(dataset, split, config, target, limit, revision, mode)
    return json.dumps(result)
}

ClassMethod Info(dataset As %String = "") As %String [ Language = python ]
{
    import json
    from hfloader import get_dataset_info

    result = get_dataset_info(dataset)
    return json.dumps(result)
}

}