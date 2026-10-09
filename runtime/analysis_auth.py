"""Opaque local credentials. Application clients cannot bypass grants via core APIs."""
from langgraph_sdk import Auth
from runtime.analysis_store import principal

auth = Auth()


@auth.authenticate
async def authenticate(headers: dict):
    header = headers.get('authorization', '')
    if not header:
        # Public identity can fetch the application shell, but no data or core API.
        return {'identity':'public','role':'public','domains':[],'is_authenticated':True}
    try:
        p = principal(header.removeprefix('Bearer '))
    except PermissionError as error:
        raise Auth.exceptions.HTTPException(status_code=401,detail=str(error)) from error
    return {'identity':p['id'],'role':p['role'],'domains':p['domains'],'permissions':['worker'] if p['role']=='worker' else ['application'],'is_authenticated':True}


@auth.on
async def core_permissions(ctx, value):
    role = getattr(ctx.user, 'role', None)
    if isinstance(ctx.user, dict):
        role = ctx.user.get('role')
    if role != 'worker' and 'worker' not in ctx.permissions:
        raise Auth.exceptions.HTTPException(status_code=403,detail='Use the role-enforced application API')
    return None
