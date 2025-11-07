# Convert *.hex to *.uf2

``` bash
git clone https://github.com/microsoft/uf2.git
cd uf2/utils
python uf2conv.py firmware_target.hex --family 0xADA52840 --output firmware_target.uf2
python uf2conv.py firmware_master.hex --family 0xADA52840 --output firmware_master.uf2
```