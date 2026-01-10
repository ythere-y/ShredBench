# ShredBench

wget https://download.blender.org/release/Blender4.0/blender-4.0.2-linux-x64.tar.xz
mkdir blender
tar -xvf blender-4.0.2-linux-x64.tar.xz -C blender --strip-components=1
rm blender-4.0.2-linux-x64.tar.xz

wget https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/120.0.6099.109/linux64/chrome-linux64.zip
unzip chrome-linux64.zip
mv chrome-linux64 chrome_bin
rm chrome-linux64.zip
