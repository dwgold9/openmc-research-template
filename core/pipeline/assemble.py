import openmc4d as mc


# ---------------------------------------------------------
# assemble: generate xml files from openmc model
# ---------------------------------------------------------
def assemble_xml(model, case_dir):
    model.export_to_xml(case_dir)