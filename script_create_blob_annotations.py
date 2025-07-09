import os
from pipeline.c_image_segmentation import segment_2d_image_with_cellpose
from pipeline.d_review_cells_manually_with_gui import review_cells_with_napari
from pipeline.e_manual_blob_annotation_gui_tool import manual_blob_annotation_gui


path_to_input_signal = '/Users/frederic/Desktop/test_segmentation_cargo/input/output/240215_GAC8_02_R3D_D3D_channel_0_membrane.tif'
path_to_brightfield = '/Users/frederic/Desktop/test_segmentation_cargo/input/output/240215_GAC8_02_R3D_D3D_channel_2_brightfield.tif'
path_to_output = os.path.dirname(path_to_brightfield)


# generate mask from brightfield
mask, path_to_mask = segment_2d_image_with_cellpose(input_brightfield_path=path_to_brightfield, output_dir=path_to_output, save_mask=True)

# manually exclude cells
excluded_txt_path = review_cells_with_napari(path_to_signal=path_to_input_signal, path_to_mask = path_to_mask,
                                             path_to_brightfield=path_to_brightfield, output_dir=path_to_output)

# annotate and manually review blobs
manual_blob_annotation_gui(path_to_signal=path_to_input_signal,path_to_brightfield=path_to_brightfield,
                           output_directory=path_to_output, show_all_detected_blobs=False)






