FROM rust:1.83 as build
WORKDIR /app
COPY Cargo.toml .
RUN mkdir src && echo 'fn main(){}' > src/main.rs && cargo build --release
COPY src ./src
RUN touch src/main.rs && cargo build --release

FROM debian:bookworm-slim
COPY --from=build /app/target/release/eagleeye-sim-api /usr/local/bin/eagleeye-sim-api
EXPOSE 8787
CMD ["eagleeye-sim-api"]
