import asyncio
from api.file_manager import FileManager

input_files = {
    "in_1": "https://nocodb.mr4web.com/dltemp/wcgw35g3D__fH1_0/1770124200000/noco/pje17e72031kkxl/mx5np916oijzdpt/clxlxwh9upkuz7f/c38473de9144a91e0014cfe06455e6c9_1769901024_ZBimE.mp4",
    "in_2": "https://nocodb.mr4web.com/dltemp/okeoqIwA0N9lYqjT/1770124200000/noco/pje17e72031kkxl/mx5np916oijzdpt/czpn6pyheg0bwvc/d8d5b16f7183508b165c47e016159160_1769901027_N0uWM.mp4",
    "in_3": "https://tempfile.aiquickdraw.com/v/d1f55176510060717b96db760065114e_1769902986.mp4",
    "in_4": "https://tempfile.aiquickdraw.com/v/cae9bd29237d2bb3da5d00a45e3dcb26_1769902978.mp4"
}

file_manager = FileManager(
    s3_bucket="dummy",
    aws_access_key_id="dummy",
    aws_secret_access_key="dummy",
    aws_region="us-east-1"
)

async def test_download():
    local_files = await file_manager.download_files(input_files)
    for k, v in local_files.items():
        print(f"{k}: {v}")
    file_manager.cleanup()

if __name__ == "__main__":
    asyncio.run(test_download())
