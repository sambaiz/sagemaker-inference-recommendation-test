from torchvision import datasets, transforms
from sagemaker.base_serializers import NumpySerializer
import tarfile
import io

if __name__ == '__main__':
  dataset = datasets.MNIST('data', train=True, transform=transforms.ToTensor(), download=True)
  serializer = NumpySerializer()
  byte_io = io.BytesIO(serializer.serialize(dataset[0][0].view(-1, 1, 28, 28)))
  with tarfile.open("sample_payload.tar.gz", "w:gz") as tar:
    tarinfo = tarfile.TarInfo(name="sample_payload")
    tarinfo.size = len(byte_io.getbuffer())
    tar.addfile(tarinfo, byte_io)