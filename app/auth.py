from fastapi import Depends, HTTPException, status 
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt,JWTError
import httpx

from app.config import settings

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
)-> str:
    
    """
    Returns the user_id from verified JWT token.
    In DEBUG mode, accepts X-user-ID header directly(no tokens)
    In production, verifies the clerk JWT signature.
    """

    #---- DEV mode-------
    #when DEBUG= True, accept a plain user ID header.
    # lets us test from swagger UI
    if settings.DEBUG:
        if credentials is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="In debug mode: pass authorization: Bearer <any-user-id>"

            )
        
        # In debug mode, we treat the token itself as the user_id
        # pass: Authorization: Bearer user_123
        return credentials.credentials
    

    #--------------- Produciton mode--------------
    if credentials is None:
        raise  HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail = "Authorization header missing",
        )
    
    token = credentials.credentials

    try:

        # fetch clerk's public keys
        async with httpx.AsyncClient() as client:
            response = await client.get(settings.CLERK_JWKS_URL)
            jwks = response.json()

        
        # decode and verify the JWT
        payload = jwt.decode(
            token,
            jwks,
            algorithms=["RS256"],
            options={"verify_aud":False},
        )

        # extract user_id from the token payload
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token : no userID found",
            )
        
        return user_id
    
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {str(e)}",
        )
    