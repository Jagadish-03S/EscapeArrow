import base64,io,re,time
from PIL import Image,UnidentifiedImageError
from fastapi import APIRouter,Depends,HTTPException,UploadFile,File
from pydantic import BaseModel,Field
from sqlalchemy import select
from ..db import db
from ..security import current,profile
from ..models import User,Review
router=APIRouter(prefix='/api',tags=['Profile and reviews'])
class Edit(BaseModel):
    username:str
    gender:str=Field(max_length=30)
class Feedback(BaseModel):
    stars:int=Field(ge=1,le=5)
    text:str=Field(default='',max_length=2000)
@router.patch('/profile')
def edit(b:Edit,u=Depends(current),s=Depends(db)):
    name=b.username.lower()
    if not re.fullmatch(r'[a-z0-9_]{3,24}',name):raise HTTPException(400,'Username needs 3-24 letters, numbers or underscores')
    other=s.scalar(select(User).where(User.username==name,User.id!=u.id))
    if other:raise HTTPException(409,'Username already used')
    u.username=name;u.gender=b.gender
    return profile(u)
@router.post('/profile/avatar')
async def avatar(file:UploadFile=File(...),u=Depends(current)):
    raw=await file.read(2*1024*1024+1)
    if len(raw)>2*1024*1024:raise HTTPException(400,'Choose an image under 2 MB')
    try:
        im=Image.open(io.BytesIO(raw))
        if im.width*im.height>20000000:raise ValueError()
        im=im.convert('RGB');im.thumbnail((256,256));out=io.BytesIO();im.save(out,format='JPEG',quality=85)
    except (UnidentifiedImageError,ValueError,OSError,Image.DecompressionBombError):raise HTTPException(400,'Invalid or oversized image')
    u.avatar='data:image/jpeg;base64,'+base64.b64encode(out.getvalue()).decode()
    return profile(u)
@router.post('/reviews')
def review(b:Feedback,u=Depends(current),s=Depends(db)):
    r=s.get(Review,u.id)
    if not r:r=Review(user_id=u.id,stars=b.stars);s.add(r)
    r.stars=b.stars;r.text=b.text;r.updated=time.time();return {'ok':True}
