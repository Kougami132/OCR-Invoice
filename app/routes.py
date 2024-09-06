from flask import Blueprint, jsonify, request, current_app
from paddleocr import PaddleOCR, draw_ocr
from .entity.boundingbox import BoundingBox
import os, office, glob, shutil

bp = Blueprint('api', __name__)

allow_extensions = ["pdf", "jpg", "png"]

# Paddleocr目前支持的多语言语种可以通过修改lang参数进行切换
# 例如`ch`, `en`, `fr`, `german`, `korean`, `japan`
ocr = PaddleOCR(use_angle_cls=True, lang="ch")  # need to run only once to download and load model into memory

@bp.route('/invoice', methods=['POST'])
def upload_file():
    try:
        # 检查请求中是否包含文件
        if 'file' not in request.files:
            return jsonify({"message": "文件不得为空"}), 400

        file = request.files['file']

        # 如果用户没有选择文件，浏览器可能会提交一个空文件而没有文件名
        if file.filename == '':
            return jsonify({"message": "文件不得为空"}), 400

        # 检查文件格式
        def get_extension(filename):
            return filename.rsplit('.', 1)[1].lower()
        def allowed_file(filename):
            return '.' in filename and get_extension(filename) in allow_extensions
        if not file or not allowed_file(file.filename):
            return jsonify({"message": "文件格式不允许"}), 400
        
        # 确认接收文件目录存在
        def ensure_directory_exists(directory_path):
            # 如果目录不存在，则创建
            if not os.path.exists(directory_path):
                os.makedirs(directory_path)
        ensure_directory_exists(os.path.join("logs", "uploads"))
        ensure_directory_exists(os.path.join("logs", "converts"))

        filename = file.filename
        filepath = os.path.join("logs", "uploads", filename)
        file.save(filepath)
        if get_extension(filename) == "pdf":
            # pdf转jpg
            office.pdf.pdf2imgs(
                pdf_path=filepath,
                out_dir=os.path.join("logs", "converts", filename)
            )
            img_path = glob.glob(os.path.join("logs", "converts", filename, "*.jpg"))[0]
        else:
            img_path = filepath

        # ocr
        result = ocr.ocr(img_path, cls=True)
        ocr_result: list[BoundingBox] = []
        for idx in range(len(result)):
            res = result[idx]
            if res == None: # 识别到空页就跳过，防止程序报错 / Skip when empty result detected to avoid TypeError:NoneType
                print(f"[DEBUG] Empty page {idx+1} detected, skip it.")
                continue
            for line in res:
                ocr_result.append(BoundingBox(line[0], line[1]))

        # 保存ocr结果
        from PIL import Image
        result = result[0]
        image = Image.open(img_path).convert('RGB')
        boxes = [line[0] for line in result]
        txts = [line[1][0] for line in result]
        scores = [line[1][1] for line in result]
        im_show = draw_ocr(image, boxes, txts, scores)
        im_show = Image.fromarray(im_show)
        im_show.save(os.path.join("logs", filename + ".jpg"))

        # 删除图片与pdf
        def delete_file_or_directory(path):
            if os.path.exists(path):
                if os.path.isfile(path):
                    os.remove(path)  # 删除文件
                elif os.path.isdir(path):
                    shutil.rmtree(path)  # 删除目录及其所有内容
        delete_file_or_directory(os.path.join("logs", "uploads", filename))
        delete_file_or_directory(os.path.join("logs", "converts", filename))
        
        # 筛选数据
        def get_items() -> list[str]:
            # 寻找项目框顶部标签位置
            def find_top_title():
                for i in ocr_result:
                    if "项目名称" in i.text or "服务名称" in i.text:
                        return i
                return None
            # 寻找项目框右边标签位置
            def find_next_title(top: BoundingBox):
                for i in range(len(ocr_result)):
                    if top.text == ocr_result[i].text:
                        return ocr_result[i + 1]
                return None
            # 寻找项目框底部标签位置
            def find_bottom_title(top: BoundingBox):
                for i in ocr_result:
                    if top.bottom < i.top and i.text in "合计":
                        return i
                for i in ocr_result:
                    if top.bottom < i.top and "合计" in i.text:
                        return i
                return None
            # 筛选出区域内的所有标签
            def find_items(top: BoundingBox, right: BoundingBox, bottom: BoundingBox) -> list[BoundingBox]:
                res = []
                for i in ocr_result:
                    if i.top > top.bottom - 3 and i.bottom < bottom.top and i.right < right.left:
                        res.append(i)
                return res
            
            top = find_top_title()
            next = find_next_title(top)
            bottom = find_bottom_title(top)
            items = find_items(top, next, bottom)
            return [i.text for i in items]
        def get_date() -> str:
            for i in ocr_result:
                if "开票日期" in i.text:
                    return i.text.replace("：", ":").replace("开票日期:", "")
        def get_amount() -> str:
            for i in ocr_result:
                if "小写" in i.text:
                    return i.text.replace("（", "(").replace("）", ")").replace("￥", "¥").replace("(小写)¥", "")
    
        return jsonify({
            "invoiceDate": get_date(),
            "totalAmount": get_amount(), 
            "invoiceDetails": [{"itemName": item} for item in get_items()]
        }), 200
    except Exception as e:
        return jsonify({"message": "识别失败," +str(e)}), 400
