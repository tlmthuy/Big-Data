# Đề cương trao đổi với giảng viên về hướng đồ án

Ngày lập: 16/11/2026. Tài liệu chuẩn bị cho buổi xin góp ý về đề tài, phạm vi và tiêu chí đánh giá; chưa phải báo cáo kết quả hoặc rubric được giảng viên xác nhận.

## 1. Điều nhóm muốn xác nhận

Nhóm dự kiến xây dựng **hệ thống gợi ý sản phẩm thương mại điện tử trên AWS**, kết hợp đánh giá chất lượng mô hình với hiệu năng xử lý dữ liệu, khả năng mở rộng và chi phí.

Hướng này phù hợp về mặt kế hoạch với `requirement.txt`: bài toán rõ, có dữ liệu thật, phân tích 5V, được sử dụng subset có tính đại diện, có so sánh và phân tích thực nghiệm. Môn không bắt buộc thuật toán mới, mô hình SOTA hoặc cloud trả phí. AWS và sáu thí nghiệm là lựa chọn trong kế hoạch riêng của nhóm.

**Chưa thể cam kết cách làm nào chắc chắn được 10 điểm.** Cần xin rubric chính thức và mô tả mức xuất sắc từ giảng viên. Những tiêu chí chất lượng bên dưới là đề xuất chuẩn bị của nhóm, không phải điều kiện điểm 10 đã được xác nhận.

## 2. Trình bày hướng đồ án bằng lời dễ hiểu

Nhóm dùng lịch sử xem hàng, thêm giỏ và mua hàng để đề xuất 20 sản phẩm phù hợp cho từng người dùng. Spark xử lý dữ liệu và phục vụ tính toán mô hình; kết quả gợi ý được tính trước, lưu trong DynamoDB. Khi nhập mã người dùng trên website, API đọc danh sách đã lưu và trả về cho giao diện. Người dùng chưa có dữ liệu được trả danh sách sản phẩm phổ biến.

Luồng hệ thống dự kiến:

```text
Dataset Kaggle
    → S3: lưu dữ liệu thô
    → Spark trên EMR: làm sạch, phân tích, chia tập và train
    → Đánh giá và tạo danh sách top-20
    → S3: file bàn giao gợi ý
    → DynamoDB: lưu theo user_id
    → API + website: tra cứu và hiển thị
```

SASRec dự kiến chạy trên Colab GPU theo tài liệu nhóm; cần thể hiện đây là phần tính toán ngoài AWS. Athena và dashboard là nhánh phân tích từ dữ liệu sạch trên S3.

Đóng góp nhóm dự kiến là tích hợp pipeline cho dataset đã chọn, thiết kế phép so sánh công bằng, triển khai và đo trên cloud, phân tích đánh đổi chất lượng–thời gian–chi phí, và cung cấp hướng dẫn tái lập. Không tuyên bố phát minh thuật toán mới.

## 3. Bốn repo mã nguồn mở đã tìm được

Các mô tả sau dựa trên nội dung công khai đã xem trong cuộc trao đổi ngày 16/11/2026. Chưa clone, audit hoặc chạy thử các repo; khả năng chạy trên dataset và môi trường nhóm chưa được kiểm chứng. Trước khi lấy code, kiểm tra LICENSE/NOTICE tại đúng commit, dependency và mức tương thích. Không cần tích hợp cả bốn repo thành bốn hệ thống riêng.

| Repo và nguồn | Có thể tận dụng | Nhóm phải bổ sung hoặc điều chỉnh | Giấy phép được công bố |
| --- | --- | --- | --- |
| [Recommenders](https://github.com/recommenders-team/recommenders) | Ví dụ ALS trên PySpark, SASRec, chuẩn bị dữ liệu, đánh giá và tuning | Adapter cho dataset nhóm; chia tập thời gian; chạy EMR; tích hợp serving AWS. Ví dụ operationalization của repo thiên về Azure | MIT |
| [RecBole](https://github.com/RUCAIBox/RecBole) | Framework Python/PyTorch để train và đánh giá nhiều mô hình, có SASRec | Chuyển dữ liệu sang định dạng yêu cầu; đồng nhất split, candidate set và metric với pipeline Spark; kiểm tra RAM/GPU | MIT |
| [Spark-RecEngine](https://github.com/ilyasakkus/Spark-RecEngine) | Theo README: PySpark ALS, tính top-N theo batch, popularity fallback, FastAPI, Docker, lưu Redis/MongoDB | Đổi storage sang DynamoDB nếu giữ kiến trúc nhóm; dùng dữ liệu thật; thêm Recall/NDCG và split phù hợp; bổ sung E1–E6 và triển khai AWS | README công bố Apache-2.0; cần kiểm tra file giấy phép tại commit trước khi lấy code |
| [AWS DynamoDB Examples](https://github.com/aws-samples/aws-dynamodb-examples) | Ví dụ SDK, thao tác DynamoDB và mẫu thiết kế liên quan | Viết loader JSONL gợi ý, schema theo user_id, API và xử lý fallback. Đây không phải repo recommender hoàn chỉnh | MIT-0 |

Nguồn bổ sung: [SASRec trong RecBole](https://github.com/RUCAIBox/RecBole/blob/master/docs/source/user_guide/model/sequential/sasrec.rst), [LICENSE RecBole](https://github.com/RUCAIBox/RecBole/blob/master/LICENSE), [LICENSE Recommenders](https://github.com/recommenders-team/recommenders/blob/main/LICENSE).

### Cách lựa chọn đề xuất

- Ưu tiên kiểm tra code nhóm đã có trước; bảng phân công ghi một số phần đã xong nhưng workspace ban đầu chưa có code để xác minh.
- Dùng Recommenders làm tài liệu và ví dụ tham khảo chính cho ALS và đánh giá.
- Chỉ chọn một implementation SASRec: RecBole hoặc bản trong Recommenders, sau khi chạy thử trên mẫu nhỏ.
- Tham khảo luồng batch-to-API của Spark-RecEngine nếu giúp tiết kiệm thời gian; không mặc định thay toàn bộ code nhóm bằng repo này.
- Tham khảo AWS DynamoDB Examples cho phần loader và tra cứu.
- Lưu repo URL, commit, giấy phép, file đã dùng và thay đổi của nhóm vào `docs/references.md` khi thực sự tái sử dụng.
- Không mang số đo, tuyên bố latency hoặc kết quả test của repo khác vào báo cáo như kết quả nhóm.

## 4. Khi gặp giảng viên cần trình bày những gì

Chuẩn bị một lượt trình bày khoảng **5 phút để xin góp ý đề tài**, tách với bài thuyết trình cuối kỳ 15 phút. Nếu buổi này có yêu cầu thời lượng riêng thì theo giảng viên.

| Thời gian gợi ý | Nội dung | Điều cần nói rõ |
| --- | --- | --- |
| 0:00–0:40 | Problem and objective | Nhóm giải bài toán top-20 recommendation từ implicit feedback; sản phẩm đầu ra là gì |
| 0:40–1:20 | Dataset and Big Data characteristics | Nguồn, trường dữ liệu, quy mô mô tả, dữ liệu thiếu; cách lấy subset và kiểm tra đại diện |
| 1:20–2:10 | Architecture | Sơ đồ S3 → Spark/EMR → gợi ý → DynamoDB → API/web; vì sao tách batch với serving |
| 2:10–3:20 | Research questions and experiments | So chất lượng mô hình; thay đổi dữ liệu/compute; đánh đổi storage/query; độ trễ phục vụ |
| 3:20–4:10 | Reuse, contribution and feasibility | Dùng repo nào cho phần nào; nhóm tự làm gì; tài nguyên, ngân sách, người phụ trách |
| 4:10–5:00 | Feedback requested | Xin xác nhận scope, rubric, subset và tiêu chí xuất sắc |

### Những thứ nên mang theo

- Một sơ đồ kiến trúc có phân biệt xử lý batch và API phục vụ.
- Một bảng E1–E6, ghi câu hỏi, biến thay đổi, chỉ số và output dự kiến.
- Nguồn dataset và một mẫu dữ liệu; nếu đã đọc dataset, mang thống kê đo thật. Nếu chưa, ghi rõ quy mô khoảng 110 triệu sự kiện/14 GB là theo mô tả trong tài liệu nhóm.
- Bảng bốn repo ở trên và ranh giới giữa code tham khảo với phần nhóm thực hiện.
- Bảng tiến độ thực tế: đã làm, đang làm, chưa làm, bằng chứng tương ứng. Không dùng `Xong` trong Excel thay cho minh chứng chạy.
- Dự toán ngân sách nếu đã có region, loại máy và thời lượng chạy; nếu chưa có thì ghi chưa xác định, không tự bịa số tiền.

## 5. Các câu hỏi thực nghiệm cần bảo vệ được

| Mã | Câu hỏi | Thiết kế dự kiến | Bằng chứng khi hoàn thành |
| --- | --- | --- | --- |
| E1 | Mô hình nào gợi ý tốt nhất trong điều kiện thử nghiệm? | Popularity, Item-CF, ALS, SASRec; cùng split và quy tắc đánh giá | Recall/NDCG@10/20, coverage, hit rate, thời gian; bảng và hình |
| E2 | Dữ liệu tăng thì thời gian xử lý tăng ra sao? | 10%, 25%, 50%, 100% theo quy tắc subset nhất quán; giữ cluster cố định | Số user/dòng/bytes thật, thời gian từng bước, biểu đồ |
| E3 | Thêm máy có nhanh hơn và có đáng tiền? | Cùng workload; cấu hình 1 máy, 2 worker, 3 worker sau khi làm rõ topology | Thời gian, speedup, tổng tài nguyên và chi phí từng run |
| E4 | CSV/Parquet và Spark/Athena khác nhau thế nào? | Ba truy vấn tương đương trên cùng dữ liệu; ghi cache, partition và compression | Kích thước, thời gian, bytes scanned/billed, chi phí có căn cứ |
| E5 | API phục vụ nhanh và ổn định đến đâu? | 1.000 user_id theo kế hoạch; ghi concurrency, warm-up và user lạ | Latency từng request, p50/p95, lỗi và timeout |
| E6 | Có dự đoán được phiên có giỏ sẽ mua hàng không? | Logistic Regression và GBT; feature chỉ dùng dữ liệu trước thời điểm dự đoán | AUC, F1, threshold, phân bố nhãn và thời gian |

Kế hoạch nhóm yêu cầu mỗi cấu hình chạy ba lần. Lưu số đo từng lần, báo mean/std khi phù hợp; với E5 phải định nghĩa rõ cách tính percentile. Không hứa mọi cấu hình full dataset trước khi xác nhận quota và ngân sách.

## 6. Cần làm gì để hướng tới mức điểm cao nhất

Đây là checklist chất lượng đề xuất, không phải bảo đảm điểm 10. Rubric 40%–20%–20%–20% và báo cáo 8–12 trang được ghi trong `Big data in Cloud.docx`; cần giảng viên xác nhận đó là rubric chính thức đang áp dụng.

| Nhóm tiêu chí trong DOCX | Việc nhóm cần làm tốt | Bằng chứng thuyết phục |
| --- | --- | --- |
| Kỹ thuật và kết quả — 40% | Pipeline chạy thật; baseline; so sánh công bằng; tránh leakage; giải thích mô hình và kết quả | Code + lệnh chạy; bảng chất lượng dữ liệu; định nghĩa split/metric; log và kết quả từng run |
| Kiến trúc và chi phí — 20% | Giải thích chọn dịch vụ, storage, batch/serving và trade-off; đo scalability và cost | Sơ đồ; cấu hình cluster; biểu đồ thời gian/speedup; chi phí có nguồn và thời gian ghi nhận |
| Báo cáo — 20% | Tiếng Anh rõ; câu hỏi gắn với thực nghiệm; hình có đơn vị; thảo luận giới hạn; trích nguồn đầy đủ | Báo cáo theo độ dài được xác nhận; bảng/hình từ số đo thật; references và hướng dẫn tái lập |
| Thuyết trình và nhóm — 20% | Phân thời gian hợp lý; cả năm người hiểu phần mình; demo rõ; Q&A có căn cứ | Bài tập dượt 15 phút; demo thật và phương án dự phòng; phân công, đóng góp và AI-use statement |

### Những điểm tạo chiều sâu nên ưu tiên

- Giải thích vì sao kết quả xảy ra: mô hình phức tạp có thể không thắng baseline; thêm worker có thể không giảm thời gian tương ứng do overhead. Kết quả bất lợi vẫn có giá trị nếu phép đo đúng và phân tích tốt.
- Đánh giá cùng một tập người dùng và cùng candidate set; không so full-ranking của một mô hình với sampled-ranking của mô hình khác rồi kết luận trực tiếp.
- Chia theo thời gian, dùng validation để tuning; giữ test cho đánh giá cuối. Không tạo feature từ tương lai.
- So CSV/Parquet trên cùng nội dung dữ liệu; tách ảnh hưởng làm sạch khỏi ảnh hưởng định dạng.
- Tách chi phí ước tính, chi phí phát sinh và credit. Nêu rõ những dịch vụ nào đã tính vào bảng.
- Kiểm tra tái lập bằng cách một người khác làm theo README trên môi trường sạch hoặc môi trường được mô tả rõ.
- Phân tích giới hạn: subset, cold start, bias dữ liệu, độ mới của gợi ý batch và phạm vi khả năng tổng quát hoá.

Không cần thêm thật nhiều công nghệ để chứng minh chất lượng. Một hệ thống có kết quả đáng tin, giải thích rõ và tái lập được thuyết phục hơn một danh sách dịch vụ chưa được kiểm chứng.

## 7. Cách hỏi giảng viên về điểm 10

### Câu mở đầu đề xuất bằng tiếng Việt

> Thưa thầy/cô, nhóm em dự kiến làm hệ thống gợi ý sản phẩm trên AWS. Nhóm muốn đánh giá cả chất lượng gợi ý lẫn hiệu năng và chi phí xử lý dữ liệu. Nhóm có tham khảo mã nguồn mở để triển khai các thuật toán, còn phần dữ liệu, tích hợp hệ thống, thiết kế thí nghiệm và đo đạc sẽ do nhóm thực hiện. Thầy/cô có thể góp ý phạm vi này đã phù hợp chưa, và để đạt mức xuất sắc, tương đương 9–10 điểm, nhóm cần cung cấp những minh chứng nào theo từng tiêu chí chấm ạ?

### Các câu cần xin xác nhận

1. **Rubric:** Thầy/cô có thể xác nhận trọng số chấm và mô tả mức đạt tối đa ở từng tiêu chí không? Điều gì phân biệt bài 8 điểm với bài 9–10 điểm?
2. **Scope:** E1–E5 đã đủ chiều sâu chưa? SASRec và E6 là phần bắt buộc của đề xuất hay có thể điều chỉnh để tập trung vào Big Data/Cloud?
3. **Subset và tài nguyên:** Nhóm được dùng subset có kiểm tra tính đại diện cho so sánh mô hình, và giới hạn quy mô thí nghiệm cloud theo ngân sách không? Có yêu cầu tối thiểu cụ thể về dữ liệu/cluster không?
4. **Mã nguồn mở:** Nhóm được tái sử dụng implementation thuật toán và khung API ở mức nào? Cần thể hiện phần tự làm và nguồn tham khảo ra sao?
5. **Bằng chứng:** Với benchmark ba lần, bảng/hình, log, cấu hình và chi phí, thầy/cô mong đợi thêm dạng minh chứng nào?
6. **Sản phẩm nộp:** Xác nhận báo cáo 8–12 trang, 15 phút trình bày + 5 phút Q&A, cả năm người nói và AI-use statement; phần nào là yêu cầu chính thức?

Ghi lại câu trả lời cụ thể thay vì chỉ hỏi “làm thế này được 10 không”. Sau buổi trao đổi, chuyển góp ý thành tiêu chí nghiệm thu có thể kiểm tra.

### English questions for the meeting

> Could you clarify what distinguishes an excellent project, in the 9–10 range, from a satisfactory one under the grading rubric?

> Is our proposed scope appropriate, or should we prioritise fewer experiments with stronger analysis? In particular, should SASRec and purchase prediction remain in scope?

> May we use a representative subset for model comparison and limit the cloud experiments to fit our budget? Are there any minimum data-size or cluster requirements?

> What level of open-source code reuse is acceptable, and how should we document our own contributions?

## 8. Đoạn giới thiệu tiếng Anh khoảng một phút

> Our proposed project is an e-commerce product recommendation system on AWS. We plan to use real browsing, cart and purchase events to generate twenty recommendations for each user.
>
> Spark on Amazon EMR will process the data and support model training. Recommendations will be computed in batches, stored in DynamoDB, and retrieved through an API and a web interface. Our planned model comparison includes Popularity, Item-CF, ALS and SASRec.
>
> Our experiments will examine recommendation quality, processing time as data volume grows, the effect of additional workers, storage and query trade-offs, and serving latency. We will use open-source implementations where appropriate and clearly document our own integration, evaluation and analysis.
>
> We would like your feedback on whether this scope is suitable and what evidence you expect for an excellent project under the grading rubric.

## 9. Thứ tự hành động sau khi được góp ý

1. Ghi rubric và phạm vi được xác nhận; thống nhất có giữ SASRec/E6 và quy mô E2/E3 không. Không tự sửa cam kết nhóm trước buổi trao đổi.
2. Kiểm tra code và hạ tầng thực có; cập nhật tiến độ dựa trên bằng chứng, xác nhận region/bucket/quota/ngân sách.
3. Chốt `docs/handoff.md` và `docs/experiments.md`: schema, split, metric, ba truy vấn E4, cấu hình chạy và nơi lưu log.
4. Hoàn thành đường đi tối thiểu trên mẫu nhỏ: dữ liệu → Popularity/ALS → file top-20 → DynamoDB → API/web, có fallback.
5. Đo baseline và kiểm tra tính đúng của đánh giá, sau đó chạy các mô hình/cấu hình còn lại trong phạm vi đã chốt.
6. Gom bằng chứng, biểu đồ và phân tích; viết báo cáo tiếng Anh; kiểm tra README; tập thuyết trình và Q&A.

### Biên bản để điền sau buổi gặp

| Nội dung | Kết luận của giảng viên | Hành động / người phụ trách |
| --- | --- | --- |
| Hướng đề tài | Chưa xác nhận | Chưa phân công |
| Rubric và mức xuất sắc | Chưa xác nhận | Chưa phân công |
| Mô hình và E1–E6 | Chưa xác nhận | Chưa phân công |
| Subset / quy mô cluster / ngân sách | Chưa xác nhận | Chưa phân công |
| Quy tắc dùng open-source và AI | Chưa xác nhận | Chưa phân công |
| Yêu cầu sản phẩm nộp và lịch | Chưa xác nhận | Chưa phân công |

## 10. Nguồn bối cảnh nội bộ

- `requirement.txt`: yêu cầu chung về dữ liệu, subset, phương pháp, triển khai, thực nghiệm và ngôn ngữ/thời lượng trình bày.
- `Big data in Cloud.docx`: hướng đề tài, AWS, mô hình, E1–E6, rubric được ghi nhận, sản phẩm và phân công.
- `Phân công đồ án Big Data in Cloud.xlsx`: mã việc, hạn, trạng thái được ghi nhận và luồng phối hợp; không dùng trạng thái này để khẳng định kết quả chạy thực tế.
- `AGENTS.md`: hướng dẫn dự án đã tổng hợp từ ba nguồn trên.
