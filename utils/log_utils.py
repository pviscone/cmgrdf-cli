import os
import ast

def get_imports_from_module(module):
    if not isinstance(module, str):
        module=module.__file__
    with open(module, "r") as file:
        tree = ast.parse(file.read(), filename=module)

    imports = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module if node.module else ""
            for alias in node.names:
                imports.append(f"{module}/{alias.name}")

    return imports

# I know, I know, paths should not be handled in this horrible way, but it's midnight.
# I get it, Mr. Clean Code. I will polish this later. I promise. Maybe.

# Recursively look for imports and copy the modules
def get_imports_and_copy(module, outfolder):
    main_dir=os.environ['CMGRDF'].rsplit("/", 1)[0]
    imports = get_imports_from_module(module)

    blacklist=["CMGRDF", "ROOT", "typing", "types", "importlib", "ast", "os", "sys", "typer"]
    for mod in imports:
        skip=False
        for black in blacklist:
            if black in mod:
                skip=True
                break
        if skip: continue
        mod=mod.replace('.','/')
        if "/" in mod:
            os.makedirs(f"{outfolder}/configs/{mod.rsplit('/',1)[0]}", exist_ok=True)
        os.system(f"cp -r --force {main_dir}/{mod}.py {outfolder}/configs/{mod}.py")
        get_imports_and_copy(f"{outfolder}/configs/{mod}.py", outfolder)


def write_log(outfolder, command, modules=[]):
    os.makedirs(f"{outfolder}/configs", exist_ok=True)
    with open(f"{outfolder}/configs/command.log", "w") as f:
        f.write(command)

    main_dir=os.environ['CMGRDF'].rsplit("/", 1)[0]
    for module in modules:
        if module is None: continue
        module_relative_path = module.__file__.split(main_dir)[1]
        module_dirpath, module_filename = module_relative_path.rsplit('/',1)
        os.makedirs(f"{outfolder}/configs/{module_dirpath}", exist_ok=True)
        os.system(f"cp -r --force {module.__file__} {outfolder}/configs/{module_dirpath}/{module_filename}")
        get_imports_and_copy(module, outfolder)
    return