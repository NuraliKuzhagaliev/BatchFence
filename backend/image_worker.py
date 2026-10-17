"""Isolated bounded decode/crop. Writes only stripped derived PNG, never source."""
import io,json,sys,warnings
from pathlib import Path


def main():
    if sys.platform!='win32':
        import resource
        resource.setrlimit(resource.RLIMIT_CPU,(4,4))
        resource.setrlimit(resource.RLIMIT_AS,(512*1024*1024,512*1024*1024))
        resource.setrlimit(resource.RLIMIT_FSIZE,(5*1024*1024,5*1024*1024))
    from PIL import Image,ImageOps
    Image.MAX_IMAGE_PIXELS=8_000_000
    warnings.simplefilter('error',Image.DecompressionBombWarning)
    raw=Path(sys.argv[1]).read_bytes()
    if len(raw)>2_000_000:raise ValueError('Image exceeds 2 MB')
    with Image.open(io.BytesIO(raw)) as original:
        if original.format not in ('PNG','JPEG','WEBP') or getattr(original,'n_frames',1)!=1:raise ValueError('Only single-frame PNG/JPEG/WebP images supported')
        if not 16<=original.width<=4096 or not 16<=original.height<=4096 or original.width*original.height>8_000_000:raise ValueError('Image dimensions/pixels exceed bounds')
        original.load();oriented=ImageOps.exif_transpose(original).convert('RGB');before=oriented.size
        crop=json.loads(sys.argv[3])
        if crop:
            x,y,w,h=crop
            if any(type(v)!=int for v in crop) or min(x,y)<0 or min(w,h)<8 or x+w>oriented.width or y+h>oriented.height:raise ValueError('Crop is outside the oriented image')
            oriented=oriented.crop((x,y,x+w,y+h))
        # Copy pixels into a new image: EXIF, ICC, comments and other metadata do
        # not travel to providers. Original authorized bytes stay separately.
        clean=Image.new('RGB',oriented.size);clean.paste(oriented);clean.save(sys.argv[2],format='PNG',optimize=False)
        print(json.dumps({'oriented_width':before[0],'oriented_height':before[1],'derived_width':clean.width,'derived_height':clean.height,
                          'crop_xywh':crop or None,'transform':'EXIF orientation -> RGB pixel copy -> optional operator crop -> metadata-free PNG','region_origin':'operator crop' if crop else 'full image; no machine localization'}))


if __name__=='__main__':main()
