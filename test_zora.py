import sys
from dspace_rest_client.client import DSpaceClient

ZORA_API_URL = 'https://www.zora.uzh.ch/server/api'

def main():
    print("connecting to ZORA API")
    
    try:

        dspace = DSpaceClient(api_endpoint=ZORA_API_URL)
        
        communities = dspace.get_communities()
        
        print("Connection Successful!")
        print(f"Found {len(communities)} top-level communities.")
        
        for community in communities:
            print(f"Community: {community.name}")
            print(f"UUID: {community.uuid}")

    except Exception as e:
        print("Connection failed")
        print(f"Error details: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()