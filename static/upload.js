$(function () {
  const fileInput = $('#fileInput');
  const uploadBtn = $('#uploadBtn');
  const progressBar = $('#progressBar');
  const progressContainer = $('.progress');

  // Initial state
  uploadBtn.prop('disabled', true);
  progressContainer.hide();

  // Enable upload button only if a file is selected
  fileInput.on('change', function () {
    uploadBtn.prop('disabled', !fileInput[0].files.length);
  });

  uploadBtn.click(function () {
    const file = fileInput[0].files[0];
    if (!file) {
      $('#fileError').removeClass('d-none');
      return;
    } else {
      $('#fileError').addClass('d-none');
    }
    

    const chunkSize = 1024 * 1024; // 1MB
    const totalChunks = Math.ceil(file.size / chunkSize);
    let currentChunk = 0;
    const uniqueFolder = generateUUID();

    // Prepare UI
    uploadBtn.prop('disabled', true);
    progressContainer.show();
    updateProgress(0);

    function uploadChunk() {
      const start = currentChunk * chunkSize;
      const end = Math.min(file.size, start + chunkSize);
      const blob = file.slice(start, end);

      const formData = new FormData();
      formData.append('file', blob);
      formData.append('chunk_index', currentChunk);
      formData.append('unique_folder', uniqueFolder);
      formData.append('filename', file.name);

      $.ajax({
        url: '/upload_chunk/',
        type: 'POST',
        data: formData,
        processData: false,
        contentType: false,
        success: function () {
          currentChunk++;
          const percent = Math.floor((currentChunk / totalChunks) * 100);
          updateProgress(percent);

          if (currentChunk < totalChunks) {
            uploadChunk();
          } else {
            // All chunks uploaded, request merge
            $.ajax({
              url: '/merge_chunks/?unique_folder=' + uniqueFolder,
              type: 'POST',
              success: function (data) {
                window.location.href = data.video_url;
              },
              error: function (xhr) {
                alert('Error during merge: ' + xhr.responseText);
                uploadBtn.prop('disabled', false);
              }
            });
          }
        },
        error: function (xhr) {
          alert('Error uploading chunk ' + currentChunk + ': ' + xhr.responseText);
          uploadBtn.prop('disabled', false);
        }
      });
    }

    uploadChunk();
  });

  function updateProgress(percent) {
    progressBar
      .css('width', percent + '%')
      .attr('aria-valuenow', percent)
      .text(percent + '%');
  }
});
