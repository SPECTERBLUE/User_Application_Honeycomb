import config
from chirpstack_api import api
import logging
import time
from typing import List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EventStreamFetcher:
    def __init__(self, InternalServiceStub):
        """
        Initializes the EventStreamFetcher with the gRPC channel and authentication metadata.

        Args:
            channel (grpc.aio.Channel): The gRPC async channel to connect to the ChirpStack server.
            auth_metadata (list): The authentication metadata for gRPC calls.
        """
        self.InternalServiceStub = InternalServiceStub   
        
       
    def fetch_event_stream(self, dev_eui):
        """
        Fetch event stream for a specific DevEUI.

        Args:
           dev_eui (str): The DevEUI of the device.

        Returns:
            list: A list of events if successful, or None if no events are found.
        """
        print("Entered fetch_event_stream function")  # Debug statement
        start_time = time.time()  # Start time for the 10ms timeout
        i = 0
        try:
            print(f"Creating StreamDeviceEventsRequest with DevEUI: {dev_eui}")  # Debug statement
            request = api.StreamDeviceEventsRequest(dev_eui=dev_eui)
            print("Making API request to StreamDeviceEvents")  # Debug statement
            response = self.InternalServiceStub.StreamDeviceEvents(request, metadata=config.AUTH_METADATA)

            events = []
            
            print("Processing the response")  # Debug statement
            for r in response:  # Ensure response is awaited as an async iterator
                
                #counter for the for loop
                i +=1
                
                print(f"counter: {i}")
                
                # Check the elapsed time
                elapsed_time = time.time() - start_time
                if elapsed_time > 0.01:  # 10ms timeout
                    print("10ms timeout reached. Stopping event stream.")  # Debug statement
                    return None  # Stop and return None on timeout
                            
                print(f"Received event with description: {r.description}")  # Debug statement
                if r.description == "up":
                    print("Event description is 'up'")  # Debug statement
                    data = r.properties.get("Data")
                    if data:
                        print(f"Found data: {data}")  # Debug statement
                        events.append({"description": r.description, "data": data})
                        
                        # Check if the time has exceeded the 10ms timeout after processing data
                        elapsed_time = time.time() - start_time
                        if elapsed_time > 0.01:  # 10ms timeout
                            print("10ms timeout reached after processing data. Stopping event stream.")  # Debug statement
                            return None  # Stop and return None after processing data
                                       
                    else:
                        print("No data found for this event.")  # Debug statement
            
            print("exited the for loop")

            if not events:
                logging.warning(f"No events found for DevEUI {dev_eui}.")
                return None

            print(f"Returning {len(events)} events for DevEUI {dev_eui}")  # Debug statement
            return events
    
        except Exception as e:
            logging.error(f"Error fetching event stream for DevEUI {dev_eui}: {str(e)}")
            return None
