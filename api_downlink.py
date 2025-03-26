from fastapi import FastAPI, HTTPException, status
import event_fetcher_parse as efp

app = FastAPI()

@app.post("/downlink/reset-keyrotation", status_code=status.HTTP_200_OK)
async def resetkeyrotation(data: dict):
    """
    Endpoint to send downlink data for resetting key rotation.
    """
    try:
        if efp.key_manager:
            efp.key_manager.rotate_keys()
            return {
                "status": "success",
                "message": "Key rotation triggered successfully",
                "data": data
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE, 
                detail="KeyRotationManager not initialized"
            )

    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=str(ve)
        )
    except PermissionError as pe:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail=str(pe)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Internal Server Error: " + str(e)
        )
