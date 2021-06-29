import Features


def build_rules():
    """
    This function builds the rules to send the remote.
    The algorithm in the function is very complex, so here are the things it do, step by step:
    1. Getting all feature function's docstring
    2. Spitting the docstring of each function to: documentation, category, echo and arguments sections.
       The documentation can be a few lines of text, presenting the content of the feature.
       The category can be obtained from the lines that contain: "Category: XXX"
           The echo can be obtained from the following line: "Echo: No", or: "Echo: Yes [ECHO_MESSAGE]"
       The arguments thing is a bit more complex. Basically, each argument can be extracted from the following line:
       ": param PARAM_NAME: ARGUMENT_DESCRIPTION [ARGUMENT_TYPE]".
       Example --> ": param x_cord: The x coordinates of the mouse [int]

    Rules structure: {"feature": {"documentation": "some docs", "category": "feature category",
     "arguments": {"arg1": ["int"], "arg2": ["choice", ["yes", "no"]]}, "echo": ["Yes", "Getting cmd output.."]}
    :return: Rules, explained above
    """
    # Initializing the rules dict
    rules = {}
    for feature in dir(Features.Features):
        # Taking every function that is not built-in
        if not feature.startswith("__"):
            # Initializing different variables
            documentation = ""
            category = ""
            echo_message = ""
            echo = False
            arguments = []

            # Getting clean lines of the current function's docstring
            doc = getattr(Features.Features, feature).__doc__
            doc = doc.split("\n")
            del(doc[0])
            for i in range(len(doc)):
                doc[i] = doc[i].strip()

            # Obtaining information from the docstring
            for i in range(len(doc)):
                # Getting category and documentation
                if doc[i].startswith("Category: "):
                    documentation = "\n".join(doc[:i])[:-1]
                    category = doc[i].split("Category: ")[1]

                # Getting echo mode
                elif doc[i].startswith("Echo: "):
                    if "[" in doc[i]:
                        echo = True
                        echo_message = doc[i].split("[")[1].replace("]", "").strip()

                # Getting arguments
                elif doc[i].startswith(":param"):
                    tmp = doc[i].split(":param ")[1]
                    relevant_info = tmp[tmp.index(":")+1:].strip()
                    splitted_info = relevant_info.split("[")
                    arg_name = splitted_info[0].strip()
                    arg_type_full = splitted_info[1].replace("]", "").strip()
                    arg_type = arg_type_full.strip()
                    dynamic = False
                    choice_id = None
                    if ":" in arg_type_full:
                        arg_type = arg_type_full.split(":")[1].split("(")[0].strip()
                        dynamic = True
                    if "(" in arg_type_full:
                        choice_id = arg_type_full.split("(")[1].replace(")", "").strip()
                    if len(splitted_info) > 2:
                        choices = splitted_info[2].replace("]", "").split(",")
                        for i in range(len(choices)):
                            choices[i] = choices[i].strip()
                        # arguments.append({arg_name: [arg_type, choices]})
                        arguments.append({"argument-name": arg_name,
                                          "argument-type": arg_type,
                                          "dynamic": dynamic,
                                          "choices": choices})
                    else:
                        if choice_id is None:
                            arguments.append({"argument-name": arg_name,
                                              "argument-type": arg_type,
                                              "dynamic": dynamic})
                        else:
                            arguments.append({"argument-name": arg_name,
                                              "argument-type": arg_type,
                                              "dynamic": dynamic,
                                              "choice-id": choice_id})

            # Adding rule to the main rules dict
            rules[feature] = {"documentation": documentation, "category": category, "echo": [echo, echo_message], "arguments": arguments}
    return rules
