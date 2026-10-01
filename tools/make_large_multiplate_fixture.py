"""Create a synthetic two-plate acceptance fixture; never overwrite inputs."""
from pathlib import Path
import json
import shutil
import sys
import xml.etree.ElementTree as ET
import zipfile

from s1_optimizer.plate_layout import stream_relocate_build_items


def main(source: Path, output: Path) -> None:
    if source.resolve() == output.resolve():
        raise ValueError("Source and fixture must differ")
    with zipfile.ZipFile(source) as original:
        settings = ET.fromstring(original.read("Metadata/model_settings.config"))
        plates = settings.findall("plate")
        if len(plates) != 1 or len(plates[0].findall("model_instance")) != 8:
            raise ValueError("Expected reviewed eight-instance tools fixture")
        first = plates[0]
        second = ET.SubElement(settings, "plate")
        ET.SubElement(second, "metadata", key="plater_id", value="2")
        ET.SubElement(second, "metadata", key="plater_name", value="SYNTHETIC large-file test")
        ET.SubElement(second, "metadata", key="locked", value="false")
        for instance in first.findall("model_instance")[4:]:
            first.remove(instance)
            second.append(instance)
        project = json.loads(original.read("Metadata/project_settings.config"))
        project["printable_area"] = ["0x0", "256x0", "256x256", "0x256"]
        project["printer_model"] = "Bambu Lab P1S"
        project["printer_settings_id"] = "SYNTHETIC 256 mm source grid"
        changes = [{"item_index": index, "dx": "307.2", "dy": "0"}
                   for index in range(4, 8)]
        with zipfile.ZipFile(output, "x") as fixture:
            for info in original.infolist():
                if info.filename == "Metadata/project_settings.config":
                    fixture.writestr(info, json.dumps(project).encode())
                elif info.filename == "Metadata/model_settings.config":
                    fixture.writestr(info, ET.tostring(settings))
                else:
                    with original.open(info) as src, fixture.open(info, "w", force_zip64=True) as dst:
                        if info.filename == "3D/3dmodel.model":
                            stream_relocate_build_items(src, dst, changes)
                        else:
                            shutil.copyfileobj(src, dst, length=1024 * 1024)
    print(output)


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
