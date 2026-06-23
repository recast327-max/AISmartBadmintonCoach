document.addEventListener('DOMContentLoaded', function() {
  // 取得圖片元素
  var image = document.getElementById('sample-image');

  // 創建Canvas元素
  var canvas = document.createElement('canvas');
  canvas.width = 1;
  canvas.height = 1;
  var ctx = canvas.getContext('2d');

  // 當圖片載入完成後
  image.onload = function() {
    // 在Canvas中繪製圖片
    ctx.drawImage(image, 0, 0, 1, 1);

    // 取得Canvas中的像素數據
    var pixelData = ctx.getImageData(0, 0, 1, 1).data;

    // 取得主要顏色的RGB值
    var color = 'rgb(' + pixelData[0] + ',' + pixelData[1] + ',' + pixelData[2] + ')';

    // 將主要顏色應用到導覽列的背景色
    document.querySelector('header').style.backgroundColor = color;
  };

  // 如果圖片載入失敗，也可以處理錯誤
  image.onerror = function() {
    console.error('圖片載入失敗');
  };
});
