import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="fpgaconvnet-optimiser-BenDev", # Replace with your own username
    version="0.0.6",
    author="Alex Montgomerie & Ben Biggs",
    author_email="am9215@ic.ac.uk bb2515@ic.ac.uk",
    description="Optimiser for mapping convolutional neural network models to FPGA platforms.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/AlexMontgomerie/fpgaconvnet-optimiser",
    include_package_data=True,
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    install_requires=[
        "networkx>=2.5",
        "numpy>=1.19.2",
        "protobuf>=3.13.0",
        "torch>=1.7.1",
        "pyyaml>=5.1.0",
        "scipy>=1.2.1",
        "torchvision>=0.8.2",
        "onnx==1.8.0",
        "onnxruntime>=1.6.0",
        "graphviz>=0.16",
        "pydot>=1.4.2",
        "onnxoptimizer>=0.2.5",
        "ddt>=1.4.2",
    ]
)