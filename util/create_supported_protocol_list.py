import os
import sys


output_file_location = "../supported_protocols.md"
input_file_location = "protocols.txt"

class Protocal_Prep(object):
    protocols = []
    
    def write_file(self, path):
        f = open(path, "w")
        
        f.write("# Supported Protocols For Dissection\n")
        f.write("Below is the full list of protocols that can be dissected and their abbreviations to tell the parser to dissect using the non-default protocol. You can provide any of the shorthands to mutiny-prep to set the dissection protocol.\n\n"+
        "## Example:\n" + 
        "### Full Protocol Name\n" + 
        "shorthand-1; shorthand-2; ... shorthand-n\n\n"+        
        "## Catalog of Protocols\n\n")
        for protos in self.protocols:
            f.write(f"### {protos[0]}\n")
            op = ""
            for name in protos[1:]:
                op += f"{name.strip()}; "
            f.write(op.strip()[:-1] + "\n\n")

    def read_file(self, path):
        f = open(path, "r")
        protos = f.readlines()
        for p in protos:
            self.protocols.append(p.split("\t"))
            
def main():
    prep = Protocal_Prep()
    prep.read_file(input_file_location)
    prep.write_file(output_file_location)
    
    
    
if __name__ == '__main__':
    main()
    
    
    
    
